"""
Bitcoin wallet — balance, history, and raw P2PKH transaction signing/broadcast.
No coincurve required; uses pure-Python ecdsa.
"""
import hashlib
import struct
import threading
from typing import Optional, Callable

import base58
from ecdsa import SigningKey, SECP256k1

BLOCKSTREAM = "https://blockstream.info/api"
MEMPOOL     = "https://mempool.space/api"


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def _varint(n: int) -> bytes:
    if n < 0xFD:   return bytes([n])
    if n <= 0xFFFF: return b"\xfd" + struct.pack("<H", n)
    if n <= 0xFFFFFFFF: return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)


def _decode_wif(wif: str) -> bytes:
    raw = base58.b58decode(wif)
    return raw[1:33]  # skip version byte; 32-byte privkey


def _compressed_pub(privkey: bytes) -> bytes:
    sk = SigningKey.from_string(privkey, curve=SECP256k1)
    vk = sk.get_verifying_key()
    x, y = vk.pubkey.point.x(), vk.pubkey.point.y()
    return (b"\x02" if y % 2 == 0 else b"\x03") + x.to_bytes(32, "big")


def _address_to_p2pkh_script(address: str) -> bytes:
    raw = base58.b58decode(address)
    h160 = raw[1:21]
    return bytes([0x76, 0xA9, 0x14]) + h160 + bytes([0x88, 0xAC])


def _der_encode_sig(r: int, s: int) -> bytes:
    """DER-encode an ECDSA (r, s) pair with low-S normalisation."""
    from ecdsa.ecdsa import generator_secp256k1
    N = generator_secp256k1.order()
    if s > N // 2:
        s = N - s

    def _enc_int(n: int) -> bytes:
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        if b[0] & 0x80:
            b = b"\x00" + b
        return b

    rb, sb = _enc_int(r), _enc_int(s)
    return bytes([0x30, 4 + len(rb) + len(sb), 0x02, len(rb)]) + rb + bytes([0x02, len(sb)]) + sb


def _sign_input(privkey: bytes, preimage: bytes) -> bytes:
    """Sign a sighash preimage; returns DER sig + SIGHASH_ALL byte."""
    sk = SigningKey.from_string(privkey, curve=SECP256k1)
    digest = _sha256d(preimage)
    r, s = sk.sign_digest(digest, sigencode=lambda r, s, _: (r, s))
    return _der_encode_sig(r, s) + bytes([0x01])


def _build_preimage(utxos: list, outputs: list, sign_idx: int) -> bytes:
    """Build the serialised tx for signing input at sign_idx (SIGHASH_ALL)."""
    tx = struct.pack("<I", 2)
    tx += _varint(len(utxos))
    for i, u in enumerate(utxos):
        tx += bytes.fromhex(u["txid"])[::-1]
        tx += struct.pack("<I", u["vout"])
        script = _address_to_p2pkh_script(u["addr"]) if i == sign_idx else b""
        tx += _varint(len(script)) + script
        tx += struct.pack("<I", 0xFFFFFFFF)
    tx += _varint(len(outputs))
    for addr, sat in outputs:
        tx += struct.pack("<Q", sat)
        sc = _address_to_p2pkh_script(addr)
        tx += _varint(len(sc)) + sc
    tx += struct.pack("<I", 0)       # locktime
    tx += struct.pack("<I", 1)       # SIGHASH_ALL
    return tx


def _build_signed_tx(privkey: bytes, utxos: list, outputs: list) -> bytes:
    """Sign every input and return the final raw transaction bytes."""
    pubkey = _compressed_pub(privkey)
    signed = []
    for i in range(len(utxos)):
        preimage  = _build_preimage(utxos, outputs, i)
        sig       = _sign_input(privkey, preimage)
        script_sig = _varint(len(sig)) + sig + _varint(len(pubkey)) + pubkey
        signed.append(script_sig)

    tx = struct.pack("<I", 2)
    tx += _varint(len(utxos))
    for i, u in enumerate(utxos):
        tx += bytes.fromhex(u["txid"])[::-1]
        tx += struct.pack("<I", u["vout"])
        tx += _varint(len(signed[i])) + signed[i]
        tx += struct.pack("<I", 0xFFFFFFFF)
    tx += _varint(len(outputs))
    for addr, sat in outputs:
        tx += struct.pack("<Q", sat)
        sc = _address_to_p2pkh_script(addr)
        tx += _varint(len(sc)) + sc
    tx += struct.pack("<I", 0)
    return tx


# ── Wallet class ──────────────────────────────────────────────────────────────

class BitcoinWallet:
    def __init__(self, address: str, private_key_wif: str = ""):
        self.address = address
        self.private_key_wif = private_key_wif

    def _net(self):
        from utils.network import get_session
        return get_session()

    def _api(self, path: str):
        for base in (BLOCKSTREAM, MEMPOOL):
            try:
                r = self._net().get(f"{base}{path}", timeout=10)
                r.raise_for_status()
                return r.json()
            except Exception:
                continue
        raise ConnectionError("All BTC API endpoints failed")

    # ── Balance ───────────────────────────────────────────────────────────────

    def get_balance(self, callback: Optional[Callable] = None) -> Optional[float]:
        def _fetch():
            try:
                d = self._api(f"/address/{self.address}")
                bal = (d["chain_stats"]["funded_txo_sum"]
                       - d["chain_stats"]["spent_txo_sum"]) / 1e8
                if callback: callback(bal, None)
                return bal
            except Exception as e:
                if callback: callback(None, str(e))
        if callback:
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            return _fetch()

    # ── Fee rates ─────────────────────────────────────────────────────────────

    def get_fee_rates(self, callback: Optional[Callable] = None):
        """Returns dict with slow/medium/fast in sat/vbyte."""
        def _fetch():
            try:
                r = self._net().get(f"{MEMPOOL}/v1/fees/recommended", timeout=8)
                r.raise_for_status()
                d = r.json()
                rates = {
                    "slow":   max(1, d.get("hourFee",      1)),
                    "medium": max(1, d.get("halfHourFee",  5)),
                    "fast":   max(1, d.get("fastestFee",  20)),
                    "unit":   "sat/vB",
                }
                if callback: callback(rates, None)
                return rates
            except Exception as e:
                if callback: callback(None, str(e))
        if callback:
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            return _fetch()

    # ── Transactions ──────────────────────────────────────────────────────────

    def get_transactions(self, callback: Optional[Callable] = None):
        def _fetch():
            try:
                raw = self._api(f"/address/{self.address}/txs")
                txs = []
                for tx in raw[:10]:
                    sent     = sum(inp["prevout"]["value"]
                                   for inp in tx.get("vin", [])
                                   if inp.get("prevout", {}).get("scriptpubkey_address") == self.address)
                    received = sum(out["value"] for out in tx.get("vout", [])
                                   if out.get("scriptpubkey_address") == self.address)
                    txs.append({
                        "txid":      tx["txid"],
                        "amount":    (received - sent) / 1e8,
                        "confirmed": tx["status"].get("confirmed", False),
                        "time":      tx["status"].get("block_time", 0) or 0,
                    })
                if callback: callback(txs, None)
                return txs
            except Exception as e:
                if callback: callback(None, str(e))
        if callback:
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            return _fetch()

    # ── Send ──────────────────────────────────────────────────────────────────

    @staticmethod
    def estimate_vsize(n_in: int, n_out: int) -> int:
        return 10 + n_in * 148 + n_out * 34

    def send(self,
             to_address: str,
             amount_btc: float,
             fee_sat_per_vb: int = 20,
             send_max: bool = False,
             callback: Optional[Callable] = None):

        def _send():
            try:
                privkey = _decode_wif(self.private_key_wif)

                # Fetch UTXOs
                raw_utxos = self._api(f"/address/{self.address}/utxo")
                if not raw_utxos:
                    raise Exception("No spendable UTXOs found in this wallet.")

                # Sort largest-first for greedy selection
                raw_utxos.sort(key=lambda u: u["value"], reverse=True)

                # Annotate each UTXO with the sender address (P2PKH script derived locally)
                utxos = [{"txid": u["txid"], "vout": u["vout"],
                          "value": u["value"], "addr": self.address}
                         for u in raw_utxos]

                total_sat = sum(u["value"] for u in utxos)

                if send_max:
                    vsize   = self.estimate_vsize(len(utxos), 1)
                    fee_sat = vsize * fee_sat_per_vb
                    send_sat = total_sat - fee_sat
                    if send_sat <= 546:
                        raise Exception("Balance too low to cover network fees.")
                    selected = utxos
                    outputs  = [(to_address, send_sat)]
                else:
                    send_sat = int(round(amount_btc * 1e8))

                    # Greedy UTXO selection
                    selected, running = [], 0
                    for u in utxos:
                        selected.append(u)
                        running += u["value"]
                        vsize   = self.estimate_vsize(len(selected), 2)
                        fee_sat = vsize * fee_sat_per_vb
                        if running >= send_sat + fee_sat:
                            break

                    if running < send_sat + fee_sat:
                        need = (send_sat + fee_sat) / 1e8
                        have = total_sat / 1e8
                        raise Exception(
                            f"Insufficient funds. Need {need:.8f} BTC "
                            f"(amount + fee), have {have:.8f} BTC."
                        )

                    change_sat = running - send_sat - fee_sat
                    outputs = [(to_address, send_sat)]
                    if change_sat > 546:   # skip dust
                        outputs.append((self.address, change_sat))

                raw_tx  = _build_signed_tx(privkey, selected, outputs)
                raw_hex = raw_tx.hex()

                # Broadcast
                r = self._net().post(f"{BLOCKSTREAM}/tx", data=raw_hex, timeout=15)
                if r.status_code == 200:
                    txid = r.text.strip()
                    if callback: callback(txid, None)
                    return txid
                else:
                    raise Exception(f"Broadcast failed ({r.status_code}): {r.text[:300]}")

            except Exception as e:
                if callback: callback(None, str(e))

        if callback:
            threading.Thread(target=_send, daemon=True).start()
        else:
            return _send()
