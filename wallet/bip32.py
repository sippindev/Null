"""
Pure-Python BIP32 / SLIP-0010 HD key derivation.
Dependencies: hashlib, hmac, struct, ecdsa, base58  (no coincurve required).
"""

import hashlib
import hmac
import struct

import base58
from ecdsa import SECP256k1, SigningKey
from ecdsa.ecdsa import generator_secp256k1

_N = generator_secp256k1.order()
_HARDENED = 0x80000000


# ── BIP39 ────────────────────────────────────────────────────────────────────

def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha512",
        mnemonic.encode("utf-8"),
        ("mnemonic" + passphrase).encode("utf-8"),
        2048,
    )


def validate_mnemonic(mnemonic: str) -> bool:
    try:
        from mnemonic import Mnemonic
        return Mnemonic("english").check(mnemonic.strip())
    except Exception:
        return False


def generate_mnemonic(words: int = 12) -> str:
    from mnemonic import Mnemonic
    return Mnemonic("english").generate(strength={12: 128, 24: 256}.get(words, 128))


# ── BIP32 secp256k1 ──────────────────────────────────────────────────────────

def _hmac512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()


def _compressed_pubkey(privkey_bytes: bytes) -> bytes:
    sk = SigningKey.from_string(privkey_bytes, curve=SECP256k1)
    vk = sk.get_verifying_key()
    x = vk.pubkey.point.x()
    y = vk.pubkey.point.y()
    return (b"\x02" if y % 2 == 0 else b"\x03") + x.to_bytes(32, "big")


class BIP32Node:
    def __init__(self, key: bytes, chain_code: bytes):
        self.key = key
        self.chain_code = chain_code

    @classmethod
    def from_seed(cls, seed: bytes) -> "BIP32Node":
        I = _hmac512(b"Bitcoin seed", seed)
        return cls(I[:32], I[32:])

    def child_private(self, index: int) -> "BIP32Node":
        hardened = index >= _HARDENED
        if hardened:
            data = b"\x00" + self.key + struct.pack(">I", index)
        else:
            data = _compressed_pubkey(self.key) + struct.pack(">I", index)
        I = _hmac512(self.chain_code, data)
        child_int = (int.from_bytes(I[:32], "big") + int.from_bytes(self.key, "big")) % _N
        return BIP32Node(child_int.to_bytes(32, "big"), I[32:])

    def derive(self, path: str) -> "BIP32Node":
        node = self
        for part in path.split("/")[1:]:
            hardened = part.endswith("'")
            idx = int(part.rstrip("'")) + (_HARDENED if hardened else 0)
            node = node.child_private(idx)
        return node

    def to_wif(self) -> str:
        raw = b"\x80" + self.key + b"\x01"  # compressed WIF
        checksum = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
        return base58.b58encode(raw + checksum).decode()

    def to_btc_address(self) -> str:
        pub = _compressed_pubkey(self.key)
        sha256d = hashlib.sha256(pub).digest()
        ripe = hashlib.new("ripemd160", sha256d).digest()
        payload = b"\x00" + ripe
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        return base58.b58encode(payload + checksum).decode()


# ── SLIP-0010 ed25519 (Solana / TON) ────────────────────────────────────────

def slip10_ed25519_derive(seed: bytes, path: str) -> bytes:
    """Derive 32-byte ed25519 private key via SLIP-0010 (hardened-only)."""
    I = _hmac512(b"ed25519 seed", seed)
    key, chain_code = I[:32], I[32:]
    for part in path.split("/")[1:]:
        idx = int(part.rstrip("'")) + _HARDENED
        data = b"\x00" + key + struct.pack(">I", idx)
        I = _hmac512(chain_code, data)
        key, chain_code = I[:32], I[32:]
    return key


def sol_address_from_seed(privkey_bytes: bytes) -> str:
    from solders.keypair import Keypair
    return str(Keypair.from_seed(privkey_bytes[:32]).pubkey())


def ton_address_from_ed25519_pubkey(pubkey_bytes: bytes) -> str:
    """
    Derive TON wallet v3R2 address (workchain 0) from an ed25519 public key.

    Uses the standard TON cell hash formula:
      data_hash       = SHA256([d1=0, d2=80] + seqno(4) + wallet_id(4) + pubkey(32))
      state_init_hash = SHA256([d1=2, d2=1] + depth_code(2) + depth_data(2)
                                + data_bits(1) + code_hash(32) + data_hash(32))
      address         = flag(1) + workchain(1) + state_init_hash(32) + crc16(2)
    """
    import base64

    # TON wallet v3R2 code cell hash — fixed bytecode, fixed hash.
    CODE_CELL_HASH = bytes.fromhex(
        "84dafa449f98a6987789ba232358072bc0f76dc4524002a5d0918b9a75d2d599"
    )

    wallet_id = 698983191
    seqno = 0

    # Data cell: 320 bits (40 bytes) leaf, no refs.
    # d1=0x00 (0 refs, level 0), d2=0x50 (floor(320/8)+ceil(320/8)=80)
    data_bytes = struct.pack(">I", seqno) + struct.pack(">I", wallet_id) + pubkey_bytes
    data_hash = hashlib.sha256(bytes([0x00, 0x50]) + data_bytes).digest()

    # StateInit cell: 5 data bits (00110), 2 refs (code + data).
    # Bits 00110 padded to byte with completion tag → 00110100 = 0x34
    # d1=0x02 (2 refs), d2=0x01 (1 data byte)
    # Depths of both refs are 0 (leaf cells) → [0x00,0x00] each
    state_init_preimage = (
        bytes([0x02, 0x01])        # d1, d2
        + bytes([0x00, 0x00])      # depth of code ref
        + bytes([0x00, 0x00])      # depth of data ref
        + bytes([0x34])            # padded data bits
        + CODE_CELL_HASH           # code cell hash
        + data_hash                # data cell hash
    )
    state_hash = hashlib.sha256(state_init_preimage).digest()

    # User-friendly address: flag=0x11 (non-bounceable) + workchain=0 + hash + CRC16
    workchain = 0
    header = bytes([0x11, workchain]) + state_hash
    crc = _crc16_xmodem(header)
    full = header + struct.pack(">H", crc)
    return base64.urlsafe_b64encode(full).decode().rstrip("=")


def _crc16_xmodem(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc
