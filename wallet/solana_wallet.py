import threading
import base64
from typing import Optional, Callable

SOL_RPCS = [
    "https://api.mainnet-beta.solana.com",
    "https://rpc.ankr.com/solana",
    "https://solana-rpc.publicnode.com",
    "https://solana-mainnet.g.alchemy.com/v2/demo",
]


class SolanaWallet:
    def __init__(self, address: str, private_key_hex: str = ""):
        self.address = address
        self.private_key_hex = private_key_hex

    def _rpc(self, method: str, params: list) -> dict:
        from utils.network import post
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        for rpc in SOL_RPCS:
            try:
                r = post(rpc, json=payload, timeout=15)
                r.raise_for_status()
                data = r.json()
                if "result" in data:
                    return data
            except Exception:
                continue
        raise ConnectionError("All Solana RPC endpoints failed")

    # ── Balance ───────────────────────────────────────────────────────────────

    def get_balance(self, callback: Optional[Callable] = None) -> Optional[float]:
        def _fetch():
            try:
                result = self._rpc("getBalance", [self.address])
                bal    = result["result"]["value"] / 1e9
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
        """Returns slow/medium/fast priority fees in microlamports/CU."""
        def _fetch():
            try:
                rates = {
                    "slow":   {"microlamports": 0,       "display": "0 (no priority)", "fee_sol": 0.000005},
                    "medium": {"microlamports": 10_000,  "display": "10k μL",           "fee_sol": 0.000005},
                    "fast":   {"microlamports": 100_000, "display": "100k μL",          "fee_sol": 0.000010},
                    "unit":   "microlamports",
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
                result = self._rpc("getSignaturesForAddress", [self.address, {"limit": 10}])
                raw    = result.get("result", [])
                txs    = [{
                    "txid":      s["signature"],
                    "amount":    None,
                    "confirmed": s.get("confirmationStatus") == "finalized",
                    "time":      s.get("blockTime", 0) or 0,
                    "error":     s.get("err"),
                } for s in raw]
                if callback: callback(txs, None)
                return txs
            except Exception as e:
                if callback: callback(None, str(e))
        if callback:
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            return _fetch()

    # ── Send ──────────────────────────────────────────────────────────────────

    def send(self,
             to_address: str,
             amount_sol: float,
             priority_microlamports: int = 10_000,
             send_max: bool = False,
             callback: Optional[Callable] = None):

        def _send():
            try:
                from solders.keypair import Keypair
                from solders.pubkey import Pubkey
                from solders.system_program import transfer, TransferParams
                from solders.message import Message
                from solders.transaction import Transaction
                from solders.hash import Hash
                from solders.compute_budget import set_compute_unit_price

                privkey_bytes = bytes.fromhex(self.private_key_hex)
                keypair       = Keypair.from_seed(privkey_bytes[:32])

                bh_data  = self._rpc("getLatestBlockhash", [{"commitment": "finalized"}])
                blockhash = Hash.from_string(bh_data["result"]["value"]["blockhash"])

                RENT_EXEMPT_MIN = 890_880  # lamports (~0.00089 SOL)

                if send_max:
                    bal_result = self._rpc("getBalance", [self.address])
                    total_lamports = bal_result["result"]["value"]
                    fee_lamports = 5000 + (priority_microlamports * 200_000 // 1_000_000)
                    lamports = total_lamports - fee_lamports - RENT_EXEMPT_MIN
                    if lamports <= 0:
                        raise Exception("Balance too low to cover fees and rent-exempt minimum.")
                else:
                    lamports = int(amount_sol * 1_000_000_000)
                    bal_result = self._rpc("getBalance", [self.address])
                    total_lamports = bal_result["result"]["value"]
                    fee_lamports = 5000 + (priority_microlamports * 200_000 // 1_000_000)
                    if total_lamports - lamports - fee_lamports < RENT_EXEMPT_MIN:
                        raise Exception(
                            f"Sending this amount would leave the account below the "
                            f"rent-exempt minimum (0.00089 SOL). Reduce the amount or use MAX."
                        )

                instructions = []
                if priority_microlamports > 0:
                    instructions.append(set_compute_unit_price(priority_microlamports))
                instructions.append(transfer(TransferParams(
                    from_pubkey=keypair.pubkey(),
                    to_pubkey=Pubkey.from_string(to_address),
                    lamports=lamports,
                )))

                msg = Message.new_with_blockhash(instructions, keypair.pubkey(), blockhash)
                tx  = Transaction.new_unsigned(msg)
                tx.sign([keypair], blockhash)

                tx_b64 = base64.b64encode(bytes(tx)).decode()
                result = self._rpc("sendTransaction", [tx_b64, {"encoding": "base64"}])
                if "error" in result:
                    raise Exception(result["error"].get("message", "RPC error"))
                txid = result.get("result", "")
                if callback: callback(txid, None)
                return txid
            except Exception as e:
                if callback: callback(None, str(e))

        if callback:
            threading.Thread(target=_send, daemon=True).start()
        else:
            return _send()
