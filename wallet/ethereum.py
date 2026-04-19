import threading
from typing import Optional, Callable

ETH_RPCS = [
    "https://eth.llamarpc.com",
    "https://rpc.ankr.com/eth",
    "https://cloudflare-eth.com",
]

ERC20_TOKENS = {
    "DAI":  {"address": "0x6B175474E89094C44Da98b954EedeAC495271d0F", "decimals": 18},
    "USDT": {"address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6},
    "USDC": {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6},
}

BALANCE_OF_ABI = [{
    "constant": True,
    "inputs": [{"name": "_owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function",
}]


def _get_w3():
    from web3 import Web3
    from utils.network import get_session
    sess = get_session()
    for rpc in ETH_RPCS:
        try:
            adapter = Web3.HTTPProvider(rpc, request_kwargs={"timeout": 8, "session": sess})
            w3 = Web3(adapter)
            if w3.is_connected():
                return w3
        except Exception:
            continue
    return Web3(Web3.HTTPProvider(ETH_RPCS[0], request_kwargs={"timeout": 8}))


class EthereumWallet:
    def __init__(self, address: str, private_key: str = ""):
        from web3 import Web3
        self.address = Web3.to_checksum_address(address) if address else address
        self.private_key = private_key

    # ── Balance ───────────────────────────────────────────────────────────────

    def get_balance(self, callback: Optional[Callable] = None) -> Optional[float]:
        def _fetch():
            try:
                w3  = _get_w3()
                bal = w3.eth.get_balance(self.address) / 1e18
                if callback: callback(bal, None)
                return bal
            except Exception as e:
                if callback: callback(None, str(e))
        if callback:
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            return _fetch()

    def get_token_balance(self, token: str, callback: Optional[Callable] = None) -> Optional[float]:
        def _fetch():
            try:
                from web3 import Web3
                info = ERC20_TOKENS.get(token)
                if not info:
                    if callback: callback(None, f"Unknown token {token}")
                    return None
                w3  = _get_w3()
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(info["address"]),
                    abi=BALANCE_OF_ABI,
                )
                raw = contract.functions.balanceOf(self.address).call()
                bal = raw / (10 ** info["decimals"])
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
        """
        Returns dict with slow/medium/fast keys.
        Each value is {"maxFeePerGas": int_wei, "maxPriorityFeePerGas": int_wei, "display": "X gwei"}.
        """
        def _fetch():
            try:
                from web3 import Web3
                w3     = _get_w3()
                latest = w3.eth.get_block("latest")
                base   = latest.get("baseFeePerGas", w3.eth.gas_price)

                tiers = {
                    "slow":   (0.5,  int(base * 1.1)),
                    "medium": (1.5,  int(base * 1.5)),
                    "fast":   (3.0,  int(base * 2.0)),
                }
                rates = {}
                for name, (tip_gwei, max_base) in tiers.items():
                    tip  = w3.to_wei(tip_gwei, "gwei")
                    mfpg = max_base + tip
                    fee_eth = (21000 * mfpg) / 1e18
                    rates[name] = {
                        "maxFeePerGas":         mfpg,
                        "maxPriorityFeePerGas": tip,
                        "display":              f"{mfpg / 1e9:.1f} gwei",
                        "fee_eth":              fee_eth,
                    }
                rates["unit"] = "gwei"
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
                from utils.network import get
                url = (
                    "https://api.etherscan.io/api"
                    f"?module=account&action=txlist&address={self.address}"
                    "&startblock=0&endblock=99999999&sort=desc&page=1&offset=10"
                )
                r    = get(url, timeout=12)
                data = r.json()
                txs  = []
                if data.get("status") == "1":
                    for tx in data["result"][:10]:
                        value    = int(tx["value"]) / 1e18
                        to_addr  = tx.get("to") or ""
                        is_in    = to_addr.lower() == self.address.lower()
                        txs.append({
                            "txid":      tx["hash"],
                            "amount":    value if is_in else -value,
                            "confirmed": int(tx.get("confirmations", 0)) > 0,
                            "time":      int(tx["timeStamp"]),
                            "from":      tx["from"],
                            "to":        to_addr,
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

    def send(self,
             to_address: str,
             amount_eth: float,
             fee_config: Optional[dict] = None,
             send_max: bool = False,
             callback: Optional[Callable] = None):

        def _send():
            try:
                from web3 import Web3
                w3      = _get_w3()
                account = w3.eth.account.from_key(self.private_key)
                to_cs   = Web3.to_checksum_address(to_address)

                # Fee calculation
                if fee_config:
                    mfpg = fee_config["maxFeePerGas"]
                    tip  = fee_config["maxPriorityFeePerGas"]
                else:
                    latest = w3.eth.get_block("latest")
                    base   = latest.get("baseFeePerGas", w3.eth.gas_price)
                    tip    = w3.to_wei(1.5, "gwei")
                    mfpg   = int(base * 1.5) + tip

                gas = 21000
                if send_max:
                    balance  = w3.eth.get_balance(account.address)
                    fee_wei  = gas * mfpg
                    send_wei = balance - fee_wei
                    if send_wei <= 0:
                        raise Exception("Balance too low to cover gas fees.")
                else:
                    send_wei = w3.to_wei(amount_eth, "ether")

                tx = {
                    "nonce":                  w3.eth.get_transaction_count(account.address),
                    "to":                     to_cs,
                    "value":                  send_wei,
                    "gas":                    gas,
                    "maxFeePerGas":           mfpg,
                    "maxPriorityFeePerGas":   tip,
                    "chainId":                1,
                    "type":                   2,
                }
                signed   = w3.eth.account.sign_transaction(tx, self.private_key)
                tx_hash  = w3.eth.send_raw_transaction(signed.raw_transaction)
                if callback: callback(tx_hash.hex(), None)
                return tx_hash.hex()
            except Exception as e:
                if callback: callback(None, str(e))

        if callback:
            threading.Thread(target=_send, daemon=True).start()
        else:
            return _send()
