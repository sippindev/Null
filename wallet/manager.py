from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from eth_account import Account

from wallet.bip32 import (
    BIP32Node,
    generate_mnemonic,
    mnemonic_to_seed,
    slip10_ed25519_derive,
    sol_address_from_seed,
    ton_address_from_ed25519_pubkey,
    validate_mnemonic,
)

# Enable once at import time, not per-call
Account.enable_unaudited_hdwallet_features()

WALLET_DIR = Path.home() / ".null_wallet"
WALLET_FILE = WALLET_DIR / "wallet.enc"

# Legacy KDF for old wallet files
_LEGACY_PBKDF2_ITERS = 480_000

# Default KDF for new wallet files (memory-hard)
_DEFAULT_SCRYPT = {"name": "scrypt", "n": 32768, "r": 8, "p": 1}


class WalletManager:
    def __init__(self):
        self._data: Optional[dict] = None
        self._ensure_wallet_dir()

    # ── Filesystem hardening ────────────────────────────────────────────────

    def _ensure_wallet_dir(self):
        # Basic local hardening: refuse to use a symlinked wallet directory.
        if WALLET_DIR.exists() and WALLET_DIR.is_symlink():
            raise RuntimeError(f"Refusing to use symlinked wallet dir: {WALLET_DIR}")

        WALLET_DIR.mkdir(exist_ok=True)
        try:
            if os.name == "posix":
                os.chmod(WALLET_DIR, 0o700)
        except Exception:
            pass

    def wallet_exists(self) -> bool:
        try:
            return WALLET_FILE.exists()
        except Exception:
            return False

    # ── Encryption helpers ──────────────────────────────────────────────────

    def _derive_fernet_key(self, password: str, salt: bytes, kdf_meta: Optional[dict]) -> bytes:
        meta = kdf_meta or {"name": "pbkdf2", "iterations": _LEGACY_PBKDF2_ITERS}
        name = meta.get("name", "pbkdf2")

        if name == "scrypt":
            n = int(meta.get("n", _DEFAULT_SCRYPT["n"]))
            r = int(meta.get("r", _DEFAULT_SCRYPT["r"]))
            p = int(meta.get("p", _DEFAULT_SCRYPT["p"]))
            kdf = Scrypt(salt=salt, length=32, n=n, r=r, p=p)
            key = kdf.derive(password.encode("utf-8"))
        else:
            iters = int(meta.get("iterations", _LEGACY_PBKDF2_ITERS))
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iters)
            key = kdf.derive(password.encode("utf-8"))

        return base64.urlsafe_b64encode(key)

    def _fernet(self, password: str, salt: bytes, kdf_meta: Optional[dict] = None) -> Fernet:
        return Fernet(self._derive_fernet_key(password, salt, kdf_meta))

    def _atomic_write_wallet_file(self, obj: dict):
        tmp = WALLET_FILE.with_suffix(WALLET_FILE.suffix + ".tmp")

        if os.name == "posix":
            fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    fd = None  # fd is now owned by the file object
                    f.write(json.dumps(obj))
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
        else:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(obj, f)

        os.replace(tmp, WALLET_FILE)
        try:
            if os.name == "posix":
                os.chmod(WALLET_FILE, 0o600)
        except Exception:
            pass

    def _derive_all(self, mnemonic: str) -> dict:
        seed = mnemonic_to_seed(mnemonic)

        # Bitcoin  m/44'/0'/0'/0/0
        btc_node = BIP32Node.from_seed(seed).derive("m/44'/0'/0'/0/0")

        # Ethereum  m/44'/60'/0'/0/0
        eth_acct = Account.from_mnemonic(mnemonic, account_path="m/44'/60'/0'/0/0")

        # Solana  m/44'/501'/0'/0'
        sol_privkey = slip10_ed25519_derive(seed, "m/44'/501'/0'/0'")

        # TON  m/44'/607'/0'/0'
        ton_privkey = slip10_ed25519_derive(seed, "m/44'/607'/0'/0'")
        from solders.keypair import Keypair as _Kp
        ton_pubkey = bytes(_Kp.from_seed(ton_privkey).pubkey())

        return {
            "btc": {
                "address": btc_node.to_btc_address(),
                "private_key": btc_node.to_wif(),
            },
            "eth": {
                "address": eth_acct.address,          # already checksummed
                "private_key": "0x" + eth_acct.key.hex(),
            },
            "sol": {
                "address": sol_address_from_seed(sol_privkey),
                "private_key": sol_privkey.hex(),
            },
            "ton": {
                "address": ton_address_from_ed25519_pubkey(ton_pubkey),
                "private_key": ton_privkey.hex(),
            },
        }

    def _save_mnemonic(self, mnemonic: str, password: str):
        """Save minimal encrypted wallet payload.

        We only store the mnemonic at rest. Keys are re-derived on unlock.
        """
        salt = os.urandom(16)
        kdf_meta = dict(_DEFAULT_SCRYPT)
        payload = {"mnemonic": mnemonic}

        enc = self._fernet(password, salt, kdf_meta).encrypt(
            json.dumps(payload).encode("utf-8")
        )

        self._atomic_write_wallet_file(
            {
                "kdf": kdf_meta,
                "salt": base64.b64encode(salt).decode("ascii"),
                "data": enc.decode("ascii"),
            }
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def create_wallet(self, password: str) -> str:
        mnemonic = generate_mnemonic(12)
        self._save_mnemonic(mnemonic, password)
        self._data = {"mnemonic": mnemonic, "keys": self._derive_all(mnemonic)}
        return mnemonic

    def import_wallet(self, mnemonic: str, password: str) -> bool:
        mnemonic = " ".join((mnemonic or "").split())
        if not validate_mnemonic(mnemonic):
            return False
        self._save_mnemonic(mnemonic, password)
        self._data = {"mnemonic": mnemonic, "keys": self._derive_all(mnemonic)}
        return True

    def unlock(self, password: str) -> bool:
        try:
            with open(WALLET_FILE, encoding="utf-8") as f:
                stored = json.load(f) or {}

            salt_b64 = stored.get("salt", "")
            data_str = stored.get("data", "")
            if not salt_b64 or not data_str:
                return False

            salt = base64.b64decode(salt_b64)
            kdf_meta = stored.get("kdf")  # None for legacy files

            dec = self._fernet(password, salt, kdf_meta).decrypt(data_str.encode("ascii"))
            payload = json.loads(dec) or {}

            mnemonic = " ".join(str(payload.get("mnemonic", "")).split())
            if not validate_mnemonic(mnemonic):
                return False

            # Re-derive keys in-memory.
            self._data = {"mnemonic": mnemonic, "keys": self._derive_all(mnemonic)}
            return True
        except InvalidToken:
            return False
        except Exception:
            return False

    def lock(self):
        self._data = None

    def is_unlocked(self) -> bool:
        return self._data is not None

    def get_address(self, chain: str) -> str:
        return (self._data or {}).get("keys", {}).get(chain, {}).get("address", "")

    def get_private_key(self, chain: str) -> str:
        return (self._data or {}).get("keys", {}).get(chain, {}).get("private_key", "")

    def get_mnemonic(self) -> str:
        return (self._data or {}).get("mnemonic", "")

    def change_password(self, current_password: str, new_password: str) -> tuple[bool, str]:
        try:
            with open(WALLET_FILE, encoding="utf-8") as f:
                stored = json.load(f) or {}

            salt_b64 = stored.get("salt", "")
            data_str = stored.get("data", "")
            if not salt_b64 or not data_str:
                return False, "Wallet file is corrupt."

            salt = base64.b64decode(salt_b64)
            kdf_meta = stored.get("kdf")

            dec = self._fernet(current_password, salt, kdf_meta).decrypt(data_str.encode("ascii"))
            payload = json.loads(dec) or {}

            mnemonic = " ".join(str(payload.get("mnemonic", "")).split())
            if not validate_mnemonic(mnemonic):
                return False, "Wallet file is corrupt."

            self._save_mnemonic(mnemonic, new_password)

            # If currently unlocked, keep in-memory state consistent.
            if self._data is not None:
                self._data = {"mnemonic": mnemonic, "keys": self._derive_all(mnemonic)}

            return True, ""
        except InvalidToken:
            return False, "Incorrect current password."
        except Exception as e:
            return False, str(e)
