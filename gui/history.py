import customtkinter as ctk
from gui import theme
from datetime import datetime

CHAINS = [
    ("btc", "BTC", theme.BTC_COLOR),
    ("eth", "ETH", theme.ETH_COLOR),
    ("sol", "SOL", theme.SOL_COLOR),
    ("ton", "TON", theme.TON_COLOR),
]


class HistoryView(ctk.CTkFrame):
    def __init__(self, parent, wallet_manager):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.wm = wallet_manager
        self._chain = "eth"
        self._tab_btns: dict = {}
        self._build()
        self._load()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=28, pady=(28, 0))
        ctk.CTkLabel(hdr, text="History",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=theme.TEXT).pack(side="left")

        tabs = ctk.CTkFrame(self, fg_color="transparent")
        tabs.pack(fill="x", padx=28, pady=14)

        for chain_key, symbol, color in CHAINS:
            btn = ctk.CTkButton(
                tabs, text=symbol, width=64, height=30, corner_radius=6,
                fg_color=color if chain_key == self._chain else theme.CARD,
                text_color=theme.TEXT, hover_color=color,
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda k=chain_key: self._switch(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._tab_btns[chain_key] = btn

        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color=theme.SURFACE, corner_radius=12,
            border_width=1, border_color=theme.BORDER,
        )
        self.list_frame.pack(fill="both", expand=True, padx=28, pady=(0, 28))

    def _switch(self, chain_key: str):
        self._chain = chain_key
        for k, btn in self._tab_btns.items():
            _, _, color = next(c for c in CHAINS if c[0] == k)
            btn.configure(fg_color=color if k == chain_key else theme.CARD)
        self._load()

    def _load(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.list_frame, text="Loading…",
                     font=ctk.CTkFont(size=14), text_color=theme.TEXT_DIM).pack(pady=40)

        chain_key = self._chain
        addr = self.wm.get_address(chain_key)

        def on_txs(txs, err):
            def _u():
                # Guard: widget may have been destroyed if user navigated away
                try:
                    if not self.list_frame.winfo_exists():
                        return
                    for w in self.list_frame.winfo_children():
                        w.destroy()
                    if err:
                        ctk.CTkLabel(self.list_frame, text=f"Error: {err}",
                                     text_color=theme.ERROR,
                                     font=ctk.CTkFont(size=13),
                                     wraplength=500).pack(pady=40)
                    elif not txs:
                        ctk.CTkLabel(self.list_frame, text="No transactions found",
                                     text_color=theme.TEXT_DIM,
                                     font=ctk.CTkFont(size=14)).pack(pady=40)
                    else:
                        for tx in txs:
                            self._tx_row(tx, chain_key)
                except Exception:
                    pass  # Widget destroyed — nothing to update

            self.after(0, _u)

        if chain_key == "btc":
            from wallet.bitcoin import BitcoinWallet
            BitcoinWallet(addr).get_transactions(on_txs)
        elif chain_key == "eth":
            from wallet.ethereum import EthereumWallet
            EthereumWallet(addr).get_transactions(on_txs)
        elif chain_key == "sol":
            from wallet.solana_wallet import SolanaWallet
            SolanaWallet(addr).get_transactions(on_txs)
        elif chain_key == "ton":
            from wallet.ton_wallet import TonWallet
            TonWallet(addr).get_transactions(on_txs)

    def _tx_row(self, tx: dict, chain_key: str):
        _, symbol, _ = next(c for c in CHAINS if c[0] == chain_key)

        row = ctk.CTkFrame(self.list_frame, fg_color=theme.CARD, corner_radius=8)
        row.pack(fill="x", padx=12, pady=4)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        txid = tx.get("txid", "")
        short = (txid[:14] + "…" + txid[-8:]) if len(txid) > 22 else txid
        ctk.CTkLabel(left, text=short,
                     font=ctk.CTkFont("Courier New", 12),
                     text_color=theme.TEXT).pack(anchor="w")

        ts = tx.get("time", 0)
        time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d  %H:%M") if ts else "Pending"
        confirmed = tx.get("confirmed", False)
        status = "✓ Confirmed" if confirmed else "⏳ Pending"
        meta = f"{time_str}   ·   {status}"
        if tx.get("error"):
            meta += "   ·   Failed"
        ctk.CTkLabel(left, text=meta,
                     font=ctk.CTkFont(size=11),
                     text_color=theme.TEXT_DIM).pack(anchor="w", pady=(2, 0))

        amount = tx.get("amount")
        if amount is not None:
            sign = "+" if amount >= 0 else ""
            amt_text = f"{sign}{amount:.6f} {symbol}"
            amt_color = theme.SUCCESS if amount >= 0 else theme.ERROR
        else:
            amt_text = f"— {symbol}"
            amt_color = theme.TEXT_DIM

        ctk.CTkLabel(inner, text=amt_text,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=amt_color).pack(side="right", anchor="center")
