import customtkinter as ctk
from gui import theme

ASSETS = [
    ("BTC", "btc", theme.BTC_COLOR),
    ("ETH", "eth", theme.ETH_COLOR),
    ("SOL", "sol", theme.SOL_COLOR),
    ("TON", "ton", theme.TON_COLOR),
]

FEE_LEVELS = ["slow", "medium", "fast"]


class SendView(ctk.CTkFrame):
    def __init__(self, parent, wallet_manager):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.wm           = wallet_manager
        self._chain       = "eth"
        self._symbol      = "ETH"
        self._color       = theme.ETH_COLOR
        self._asset_btns: dict = {}
        self._fee_btns:   dict = {}
        self._fee_level   = "medium"
        self._fee_rates   = {}         # populated from network
        self._balance     = None
        self._custom_fee_var = None
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        ctk.CTkLabel(self, text="Send",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=theme.TEXT).pack(anchor="w", padx=28, pady=(28, 20))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=28, pady=0)

        # ── Asset selector ────────────────────────────────────────────────────
        ctk.CTkLabel(scroll, text="ASSET",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=theme.TEXT_DIM).pack(anchor="w", pady=(0, 8))

        asset_row = ctk.CTkFrame(scroll, fg_color="transparent")
        asset_row.pack(anchor="w", pady=(0, 22))

        for sym, ck, ac in ASSETS:
            btn = ctk.CTkButton(
                asset_row, text=sym, width=70, height=36,
                corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=ac if ck == self._chain else theme.CARD,
                text_color=theme.TEXT, hover_color=ac,
                command=lambda s=sym, k=ck, c=ac: self._select(s, k, c),
            )
            btn.pack(side="left", padx=(0, 8))
            self._asset_btns[ck] = btn

        # ── Form card ─────────────────────────────────────────────────────────
        card = ctk.CTkFrame(scroll, fg_color=theme.SURFACE, corner_radius=12,
                            border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=(0, 20))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=22)

        # FROM
        ctk.CTkLabel(inner, text="FROM",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=theme.TEXT_DIM).pack(anchor="w", pady=(0, 4))
        self.from_lbl = ctk.CTkLabel(inner, text="",
                                      font=ctk.CTkFont("Courier New", 12),
                                      text_color=theme.TEXT_DIM)
        self.from_lbl.pack(anchor="w", pady=(0, 16))

        # RECIPIENT
        ctk.CTkLabel(inner, text="RECIPIENT",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=theme.TEXT_DIM).pack(anchor="w", pady=(0, 4))
        self.to_entry = ctk.CTkEntry(inner, placeholder_text="Paste address here",
                                     height=42, fg_color=theme.CARD, border_color=theme.BORDER,
                                     text_color=theme.TEXT, font=ctk.CTkFont("Courier New", 12))
        self.to_entry.pack(fill="x", pady=(0, 16))

        # AMOUNT row  [entry] [MAX] [symbol]
        ctk.CTkLabel(inner, text="AMOUNT",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=theme.TEXT_DIM).pack(anchor="w", pady=(0, 4))

        amt_row = ctk.CTkFrame(inner, fg_color="transparent")
        amt_row.pack(fill="x", pady=(0, 16))
        amt_row.columnconfigure(0, weight=1)

        self.amt_entry = ctk.CTkEntry(amt_row, placeholder_text="0.00000000",
                                      height=42, fg_color=theme.CARD, border_color=theme.BORDER,
                                      text_color=theme.TEXT, font=ctk.CTkFont(size=18))
        self.amt_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(amt_row, text="MAX", width=52, height=42,
                      fg_color=theme.BORDER, text_color=theme.TEXT_DIM,
                      hover_color=theme.CARD, corner_radius=8,
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._set_max).grid(row=0, column=1, padx=(0, 6))

        self.sym_lbl = ctk.CTkLabel(amt_row, text="ETH", width=44,
                                     font=ctk.CTkFont(size=16, weight="bold"),
                                     text_color=self._color)
        self.sym_lbl.grid(row=0, column=2)

        # Balance hint
        self.bal_hint = ctk.CTkLabel(inner, text="",
                                      font=ctk.CTkFont(size=11),
                                      text_color=theme.TEXT_DIM)
        self.bal_hint.pack(anchor="w", pady=(0, 16))

        # ── Fee selector ──────────────────────────────────────────────────────
        ctk.CTkLabel(inner, text="NETWORK FEE",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=theme.TEXT_DIM).pack(anchor="w", pady=(0, 8))

        fee_card = ctk.CTkFrame(inner, fg_color=theme.CARD, corner_radius=8,
                                border_width=1, border_color=theme.BORDER)
        fee_card.pack(fill="x", pady=(0, 4))
        fee_inner = ctk.CTkFrame(fee_card, fg_color="transparent")
        fee_inner.pack(fill="x", padx=12, pady=12)

        # Tier buttons
        tier_row = ctk.CTkFrame(fee_inner, fg_color="transparent")
        tier_row.pack(fill="x", pady=(0, 10))

        labels = {"slow": "Slow", "medium": "Medium", "fast": "Fast"}
        for lvl in FEE_LEVELS:
            btn = ctk.CTkButton(
                tier_row, text=labels[lvl], height=34,
                corner_radius=6, font=ctk.CTkFont(size=12),
                fg_color=self._color if lvl == self._fee_level else theme.SURFACE,
                text_color=theme.TEXT,
                hover_color=self._color,
                command=lambda l=lvl: self._set_fee_level(l),
            )
            btn.pack(side="left", expand=True, fill="x", padx=(0, 6))
            self._fee_btns[lvl] = btn

        # Custom fee row
        custom_row = ctk.CTkFrame(fee_inner, fg_color="transparent")
        custom_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(custom_row, text="Custom:", font=ctk.CTkFont(size=12),
                     text_color=theme.TEXT_DIM, width=54).pack(side="left")

        self._custom_fee_var = ctk.StringVar()
        self._custom_fee_entry = ctk.CTkEntry(
            custom_row, textvariable=self._custom_fee_var,
            placeholder_text="e.g. 30", width=80, height=30,
            fg_color=theme.SURFACE, border_color=theme.BORDER,
            text_color=theme.TEXT, font=ctk.CTkFont(size=12),
        )
        self._custom_fee_entry.pack(side="left", padx=(0, 8))
        self._custom_fee_entry.bind("<FocusIn>",  lambda _: self._on_custom_focus())
        self._custom_fee_entry.bind("<KeyRelease>", lambda _: self._update_fee_display())

        self.fee_unit_lbl = ctk.CTkLabel(custom_row, text="sat/vB",
                                          font=ctk.CTkFont(size=11),
                                          text_color=theme.TEXT_MUTED)
        self.fee_unit_lbl.pack(side="left")

        # Fee display line
        self.fee_display = ctk.CTkLabel(fee_inner, text="Fetching fee rates…",
                                         font=ctk.CTkFont(size=12),
                                         text_color=theme.TEXT_DIM)
        self.fee_display.pack(anchor="w", pady=(4, 0))

        # ── Status + Send ─────────────────────────────────────────────────────
        self.status_lbl = ctk.CTkLabel(inner, text="",
                                        font=ctk.CTkFont(size=12),
                                        text_color=theme.ERROR, wraplength=460)
        self.status_lbl.pack(anchor="w", pady=(12, 8))

        self.send_btn = ctk.CTkButton(inner, text="Send Transaction",
                                       height=48, corner_radius=10,
                                       fg_color=theme.TEXT, text_color=theme.BG,
                                       hover_color="#D0D0D0",
                                       font=ctk.CTkFont(size=15, weight="bold"),
                                       command=self._send)
        self.send_btn.pack(fill="x")

        self._update_from()
        self._update_fee_unit()
        self._fetch_fee_rates()
        self._fetch_balance()

    # ── Asset selection ───────────────────────────────────────────────────────

    def _select(self, symbol: str, chain_key: str, color: str):
        self._chain  = chain_key
        self._symbol = symbol
        self._color  = color

        for k, btn in self._asset_btns.items():
            btn_c = next(ac for _, ck, ac in ASSETS if ck == k)
            btn.configure(fg_color=btn_c if k == chain_key else theme.CARD)

        self.sym_lbl.configure(text=symbol, text_color=color)
        self.status_lbl.configure(text="")
        self._update_from()
        self._update_fee_unit()
        self._fetch_fee_rates()
        self._fetch_balance()

        # Reset fee tier buttons to match new chain colour
        for lvl, btn in self._fee_btns.items():
            btn.configure(
                fg_color=color if lvl == self._fee_level else theme.SURFACE,
                hover_color=color,
            )

    def _update_from(self):
        addr  = self.wm.get_address(self._chain)
        short = (addr[:14] + "…" + addr[-10:]) if len(addr) > 24 else addr
        self.from_lbl.configure(text=short)

    # ── Fee rates ─────────────────────────────────────────────────────────────

    def _fetch_fee_rates(self):
        self.fee_display.configure(text="Fetching fee rates…", text_color=theme.TEXT_DIM)
        chain = self._chain

        def callback(rates, err):
            def _u():
                try:
                    if not self.fee_display.winfo_exists(): return
                    if err or not rates:
                        self.fee_display.configure(text="Could not fetch rates",
                                                    text_color=theme.WARNING)
                        return
                    self._fee_rates = rates
                    self._update_fee_display()
                except Exception: pass
            self.after(0, _u)

        if chain == "btc":
            from wallet.bitcoin import BitcoinWallet
            BitcoinWallet(self.wm.get_address("btc")).get_fee_rates(callback)
        elif chain == "eth":
            from wallet.ethereum import EthereumWallet
            EthereumWallet(self.wm.get_address("eth")).get_fee_rates(callback)
        elif chain == "sol":
            from wallet.solana_wallet import SolanaWallet
            SolanaWallet(self.wm.get_address("sol")).get_fee_rates(callback)
        elif chain == "ton":
            self.fee_display.configure(text="TON fees: ~0.005 TON (send unavailable)",
                                        text_color=theme.WARNING)
            self._fee_rates = {}

    def _set_fee_level(self, level: str):
        self._fee_level = level
        self._custom_fee_var.set("")
        for lvl, btn in self._fee_btns.items():
            btn.configure(fg_color=self._color if lvl == level else theme.SURFACE)
        self._update_fee_display()

    def _on_custom_focus(self):
        # Deselect preset buttons when user types a custom value
        self._fee_level = "custom"
        for btn in self._fee_btns.values():
            btn.configure(fg_color=theme.SURFACE)

    def _get_active_fee(self):
        """Return the fee value for the active selection, or None if unknown."""
        if self._fee_level == "custom":
            try:
                return float(self._custom_fee_var.get())
            except ValueError:
                return None
        return self._fee_rates.get(self._fee_level)

    def _update_fee_display(self):
        try:
            if not self.fee_display.winfo_exists(): return
        except Exception:
            return

        unit = self._fee_rates.get("unit", "")
        level_data = self._fee_rates.get(self._fee_level)

        if self._fee_level == "custom":
            val = self._custom_fee_var.get()
            if val:
                self.fee_display.configure(text=f"Custom: {val} {unit}",
                                            text_color=theme.TEXT_DIM)
            else:
                self.fee_display.configure(text="Enter custom fee above",
                                            text_color=theme.TEXT_DIM)
            return

        if not level_data:
            self.fee_display.configure(text="Rates unavailable", text_color=theme.WARNING)
            return

        if isinstance(level_data, dict):
            disp = level_data.get("display", "")
            fee_native = level_data.get("fee_eth") or level_data.get("fee_sol")
            if fee_native is not None:
                sym = "ETH" if self._chain == "eth" else "SOL"
                self.fee_display.configure(
                    text=f"{self._fee_level.title()}: {disp}  ·  ≈ {fee_native:.6f} {sym}",
                    text_color=theme.TEXT_DIM,
                )
            else:
                self.fee_display.configure(text=f"{self._fee_level.title()}: {disp}",
                                            text_color=theme.TEXT_DIM)
        else:
            # BTC: plain int (sat/vB)
            vsize   = 10 + 1 * 148 + 2 * 34   # typical 1-in 2-out estimate
            fee_sat = vsize * int(level_data)
            self.fee_display.configure(
                text=f"{self._fee_level.title()}: {level_data} sat/vB  ·  ≈ {fee_sat/1e8:.8f} BTC",
                text_color=theme.TEXT_DIM,
            )

    def _update_fee_unit(self):
        units = {"btc": "sat/vB", "eth": "gwei", "sol": "μL", "ton": "—"}
        self.fee_unit_lbl.configure(text=units.get(self._chain, ""))

    # ── Balance / MAX ─────────────────────────────────────────────────────────

    def _fetch_balance(self):
        self._balance = None
        self.bal_hint.configure(text="")
        chain = self._chain

        def cb(bal, err):
            def _u():
                try:
                    if not self.bal_hint.winfo_exists(): return
                    if bal is not None:
                        self._balance = bal
                        sym = next(s for s, k, _ in ASSETS if k == chain)
                        self.bal_hint.configure(
                            text=f"Available: {bal:.6f} {sym}",
                            text_color=theme.TEXT_DIM,
                        )
                except Exception: pass
            self.after(0, _u)

        if chain == "btc":
            from wallet.bitcoin import BitcoinWallet
            BitcoinWallet(self.wm.get_address("btc")).get_balance(cb)
        elif chain == "eth":
            from wallet.ethereum import EthereumWallet
            EthereumWallet(self.wm.get_address("eth")).get_balance(cb)
        elif chain == "sol":
            from wallet.solana_wallet import SolanaWallet
            SolanaWallet(self.wm.get_address("sol")).get_balance(cb)
        elif chain == "ton":
            from wallet.ton_wallet import TonWallet
            TonWallet(self.wm.get_address("ton")).get_balance(cb)

    def _set_max(self):
        if self._balance is None:
            self.status_lbl.configure(text="Balance not loaded yet — wait a moment.",
                                       text_color=theme.WARNING)
            return

        chain = self._chain
        fee_data = self._get_active_fee()

        if chain == "btc":
            fee_rate = int(fee_data) if isinstance(fee_data, (int, float)) and fee_data else 20
            vsize    = 10 + 1 * 148 + 1 * 34   # send_max: no change output
            fee_btc  = vsize * fee_rate / 1e8
            max_val  = max(0.0, self._balance - fee_btc)
        elif chain == "eth":
            if isinstance(fee_data, dict):
                fee_wei = 21000 * fee_data["maxFeePerGas"]
            else:
                fee_wei = 21000 * 50_000_000_000   # 50 gwei fallback
            max_val = max(0.0, self._balance - fee_wei / 1e18)
        elif chain == "sol":
            max_val = max(0.0, self._balance - 0.000010)   # ~10k lamports fee
        else:
            max_val = self._balance

        self.amt_entry.delete(0, "end")
        self.amt_entry.insert(0, f"{max_val:.8f}")
        self.status_lbl.configure(text="")

    # ── Send ──────────────────────────────────────────────────────────────────

    def _send(self):
        if self._chain == "ton":
            self.status_lbl.configure(
                text="TON send not available on Python 3.14 (coincurve build issue). "
                     "Use Tonkeeper with your seed phrase to send TON.",
                text_color=theme.WARNING,
            )
            return

        to_addr  = self.to_entry.get().strip()
        amt_str  = self.amt_entry.get().strip()
        send_max = (amt_str == self.amt_entry.get()
                    and self._balance is not None
                    and amt_str.lstrip("0").rstrip("0").rstrip(".") ==
                    f"{self._balance:.8f}".lstrip("0").rstrip("0").rstrip("."))

        if not to_addr:
            self.status_lbl.configure(text="Enter a recipient address.", text_color=theme.ERROR)
            return
        if not amt_str:
            self.status_lbl.configure(text="Enter an amount.", text_color=theme.ERROR)
            return
        try:
            amount = float(amt_str)
            assert amount > 0
        except (ValueError, AssertionError):
            self.status_lbl.configure(text="Enter a valid positive amount.", text_color=theme.ERROR)
            return

        fee_data = self._get_active_fee()
        if fee_data is None and self._fee_level == "custom":
            self.status_lbl.configure(text="Enter a valid custom fee.", text_color=theme.ERROR)
            return

        self.send_btn.configure(state="disabled", text="Sending…")
        self.status_lbl.configure(text=f"Broadcasting {amount} {self._symbol}…",
                                   text_color=theme.TEXT_DIM)

        pk    = self.wm.get_private_key(self._chain)
        addr  = self.wm.get_address(self._chain)
        chain = self._chain

        def on_done(txid, err):
            def _u():
                try:
                    if not self.send_btn.winfo_exists(): return
                    self.send_btn.configure(state="normal", text="Send Transaction")
                    if err:
                        self.status_lbl.configure(text=f"Error: {err}", text_color=theme.ERROR)
                    else:
                        short = (txid[:22] + "…") if txid and len(txid) > 22 else (txid or "")
                        self.status_lbl.configure(
                            text=f"✓ Sent!  TX: {short}", text_color=theme.SUCCESS
                        )
                        self.to_entry.delete(0, "end")
                        self.amt_entry.delete(0, "end")
                        self._fetch_balance()
                        from gui.toast import show as _toast
                        _toast(self.winfo_toplevel(),
                               f"{self._symbol} Sent",
                               f"{amount} {self._symbol} → {to_addr[:16]}…")
                except Exception: pass
            self.after(0, _u)

        if chain == "btc":
            from wallet.bitcoin import BitcoinWallet
            fee_rate = int(fee_data) if isinstance(fee_data, (int, float)) and fee_data else 20
            BitcoinWallet(addr, pk).send(to_addr, amount, fee_sat_per_vb=fee_rate,
                                          send_max=send_max, callback=on_done)
        elif chain == "eth":
            from wallet.ethereum import EthereumWallet
            fc = fee_data if isinstance(fee_data, dict) else None
            EthereumWallet(addr, pk).send(to_addr, amount, fee_config=fc,
                                           send_max=send_max, callback=on_done)
        elif chain == "sol":
            from wallet.solana_wallet import SolanaWallet
            prio = int(fee_data.get("microlamports", 10_000)) if isinstance(fee_data, dict) else 10_000
            SolanaWallet(addr, pk).send(to_addr, amount,
                                         priority_microlamports=prio,
                                         send_max=send_max, callback=on_done)
