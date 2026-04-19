import customtkinter as ctk
from gui import theme

CHAINS = [
    ("btc", "Bitcoin",  "BTC", theme.BTC_COLOR, ["BTC"]),
    ("eth", "Ethereum", "ETH", theme.ETH_COLOR, ["DAI", "USDT", "USDC"]),
    ("sol", "Solana",   "SOL", theme.SOL_COLOR, []),
    ("ton", "TON",      "TON", theme.TON_COLOR, []),
]


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, wallet_manager):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.wm = wallet_manager
        self._labels: dict = {}
        self._build()
        self._refresh()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=28, pady=(28, 0))

        ctk.CTkLabel(hdr, text="Portfolio",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=theme.TEXT).pack(side="left", anchor="center")

        self._refresh_btn = ctk.CTkButton(
            hdr, text="↻  Refresh", width=110, height=32,
            fg_color=theme.CARD, text_color=theme.TEXT_DIM,
            hover_color=theme.BORDER, corner_radius=8,
            font=ctk.CTkFont(size=12),
            command=self._refresh,
        )
        self._refresh_btn.pack(side="right", anchor="center")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=20, pady=16)
        grid.columnconfigure((0, 1), weight=1, uniform="col")
        grid.rowconfigure((0, 1), weight=1, uniform="row")

        positions = {"btc": (0, 0), "eth": (0, 1), "sol": (1, 0), "ton": (1, 1)}

        for chain_key, name, symbol, color, tokens in CHAINS:
            r, c = positions[chain_key]
            card = self._make_card(grid, chain_key, name, symbol, color, tokens)
            card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

    def _make_card(self, parent, chain_key, name, symbol, color, tokens):
        card = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=12,
                            border_width=1, border_color=theme.BORDER)

        accent = ctk.CTkFrame(card, fg_color=color, height=3, corner_radius=0)
        accent.pack(fill="x")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=14)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=name,
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=theme.TEXT).pack(side="left")
        ctk.CTkLabel(top, text=symbol,
                     font=ctk.CTkFont(size=11),
                     text_color=color).pack(side="right")

        addr = self.wm.get_address(chain_key)
        short = (addr[:10] + "…" + addr[-6:]) if len(addr) > 16 else addr
        ctk.CTkLabel(inner, text=short,
                     font=ctk.CTkFont("Courier New", 10),
                     text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(4, 10))

        bal_lbl = ctk.CTkLabel(inner, text="—",
                               font=ctk.CTkFont(size=22, weight="bold"),
                               text_color=theme.TEXT)
        bal_lbl.pack(anchor="w")
        self._labels[chain_key] = bal_lbl

        if tokens:
            tok_frame = ctk.CTkFrame(inner, fg_color="transparent")
            tok_frame.pack(fill="x", pady=(10, 0))
            for tok in tokens:
                row = ctk.CTkFrame(tok_frame, fg_color="transparent")
                row.pack(fill="x", pady=1)
                ctk.CTkLabel(row, text=tok, font=ctk.CTkFont(size=11),
                             text_color=theme.TEXT_DIM).pack(side="left")
                lbl = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(size=11),
                                   text_color=theme.TEXT_DIM)
                lbl.pack(side="right")
                self._labels[f"eth_{tok.lower()}"] = lbl

        return card

    def _set_lbl(self, key: str, text: str, color=None):
        """Thread-safe label update with existence guard."""
        def _u():
            try:
                lbl = self._labels.get(key)
                if lbl and lbl.winfo_exists():
                    lbl.configure(text=text, text_color=color or theme.TEXT)
            except Exception:
                pass
        self.after(0, _u)

    def _refresh(self):
        if not self._refresh_btn.winfo_exists():
            return
        self._refresh_btn.configure(state="disabled", text="…")

        # Track how many callbacks are still pending
        pending = [7]  # btc + eth + dai + usdt + usdc + sol + ton

        def done():
            pending[0] -= 1
            if pending[0] <= 0:
                def _re():
                    try:
                        if self._refresh_btn.winfo_exists():
                            self._refresh_btn.configure(state="normal", text="↻  Refresh")
                    except Exception:
                        pass
                self.after(0, _re)

        from wallet.bitcoin import BitcoinWallet
        from wallet.ethereum import EthereumWallet
        from wallet.solana_wallet import SolanaWallet
        from wallet.ton_wallet import TonWallet

        def cb_btc(b, e):
            self._set_lbl("btc", f"{b:.6f} BTC" if b is not None else "Error",
                          theme.TEXT if b is not None else theme.ERROR)
            done()

        def cb_eth(b, e):
            self._set_lbl("eth", f"{b:.6f} ETH" if b is not None else "Error",
                          theme.TEXT if b is not None else theme.ERROR)
            done()

        def cb_sol(b, e):
            self._set_lbl("sol", f"{b:.6f} SOL" if b is not None else "Error",
                          theme.TEXT if b is not None else theme.ERROR)
            done()

        def cb_ton(b, e):
            self._set_lbl("ton", f"{b:.4f} TON" if b is not None else "Error",
                          theme.TEXT if b is not None else theme.ERROR)
            done()

        BitcoinWallet(self.wm.get_address("btc")).get_balance(cb_btc)

        eth_w = EthereumWallet(self.wm.get_address("eth"))
        eth_w.get_balance(cb_eth)

        for tok in ["DAI", "USDT", "USDC"]:
            def cb_tok(b, e, tk=tok):
                self._set_lbl(f"eth_{tk.lower()}",
                              f"{b:.2f} {tk}" if b is not None else "—",
                              theme.TEXT_DIM)
                done()
            eth_w.get_token_balance(tok, cb_tok)

        SolanaWallet(self.wm.get_address("sol")).get_balance(cb_sol)
        TonWallet(self.wm.get_address("ton")).get_balance(cb_ton)
