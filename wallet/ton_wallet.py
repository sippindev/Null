import os
import threading
from typing import Optional, Callable

from utils.network import get_session

TONCENTER = "https://toncenter.com/api/v2"
TONAPI = "https://tonapi.io/v2"


class TonWallet:
    def __init__(self, address: str, private_key_hex: str = ""):
        self.address = address
        self.private_key_hex = private_key_hex

    def _net(self):
        return get_session()

    def _toncenter_params(self, extra: dict) -> dict:
        # Optional: allow users to set TONCenter key without storing it.
        api_key = os.environ.get("TONCENTER_API_KEY", "").strip()
        params = dict(extra or {})
        if api_key:
            params["api_key"] = api_key
        return params

    def get_balance(self, callback: Optional[Callable] = None) -> Optional[float]:
        def _fetch():
            try:
                # Prefer TONAPI (often works without API keys)
                r = self._net().get(f"{TONAPI}/accounts/{self.address}", timeout=12)
                r.raise_for_status()
                d = r.json() or {}
                if "balance" in d:
                    bal = int(d.get("balance", 0)) / 1e9
                    if callback:
                        callback(bal, None)
                    return bal

                # Fallback: TONCenter
                r2 = self._net().get(
                    f"{TONCENTER}/getAddressBalance",
                    params=self._toncenter_params({"address": self.address}),
                    timeout=12,
                )
                r2.raise_for_status()
                d2 = r2.json() or {}
                if d2.get("ok"):
                    bal = int(d2.get("result", 0)) / 1e9
                    if callback:
                        callback(bal, None)
                    return bal

                raise Exception(d2.get("error", "TON balance lookup failed"))
            except Exception as e:
                if callback:
                    callback(None, str(e))

        if callback:
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            return _fetch()

    def get_transactions(self, callback: Optional[Callable] = None):
        def _fetch():
            try:
                # TONAPI attempt (endpoint varies; parse defensively)
                r = self._net().get(
                    f"{TONAPI}/accounts/{self.address}/transactions",
                    params={"limit": 10},
                    timeout=12,
                )
                if r.status_code == 200:
                    raw = r.json() or []
                    if isinstance(raw, dict):
                        raw = raw.get("transactions") or raw.get("result") or []

                    txs = []
                    if isinstance(raw, list):
                        for tx in raw[:10]:
                            txid = tx.get("hash") or tx.get("transaction_id") or ""
                            utime = tx.get("utime") or tx.get("timestamp") or 0
                            txs.append({
                                "txid": txid,
                                "amount": None,
                                "confirmed": True,
                                "time": int(utime) if utime else 0,
                            })

                    if callback:
                        callback(txs, None)
                    return txs

                # Fallback: TONCenter
                r2 = self._net().get(
                    f"{TONCENTER}/getTransactions",
                    params=self._toncenter_params({"address": self.address, "limit": 10}),
                    timeout=12,
                )
                r2.raise_for_status()
                data = r2.json() or {}
                txs = []
                if data.get("ok"):
                    for tx in (data.get("result") or [])[:10]:
                        in_msg = tx.get("in_msg", {}) or {}
                        out_msgs = tx.get("out_msgs", []) or []
                        val_in = int(in_msg.get("value", 0)) / 1e9
                        val_out = sum(int(m.get("value", 0)) for m in out_msgs) / 1e9
                        txs.append({
                            "txid": tx.get("transaction_id", {}).get("hash", ""),
                            "amount": val_in - val_out,
                            "confirmed": True,
                            "time": tx.get("utime", 0) or 0,
                        })

                if callback:
                    callback(txs, None)
                return txs
            except Exception as e:
                if callback:
                    callback(None, str(e))

        if callback:
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            return _fetch()

    def send(self, to_address: str, amount_ton: float, callback: Optional[Callable] = None):
        # Sending TON requires the tonsdk / pytonlib library which depends on
        # coincurve — that package cannot be built on Python 3.14 yet.
        # TON receive works correctly; for sending use Tonkeeper or Tonhub.
        def _send():
            err = (
                "TON send requires 'tonsdk' which cannot be installed on Python 3.14. "
                "Use Tonkeeper or any TON wallet to send — import your seed phrase there."
            )
            if callback:
                callback(None, err)

        if callback:
            threading.Thread(target=_send, daemon=True).start()
        else:
            _send()
