import threading
import customtkinter as ctk
from gui import theme


NAV = [
    ("dashboard",        "Dashboard"),
    ("send",             "Send"),
    ("receive",          "Receive"),
    ("history",          "History"),
    ("privacy_network",  "Privacy & Network"),
    ("settings",         "Settings"),
]


class MainLayout(ctk.CTkFrame):
    def __init__(self, parent, wallet_manager):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.wm = wallet_manager
        self._nav_btns: dict = {}

        # Cache views so switching tabs is instant after first open.
        self._views: dict = {}
        self._current_view = None

        self._build()

    def _build(self):
        # ── Sidebar ──────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(self, fg_color=theme.SIDEBAR_BG, corner_radius=0,
                               width=theme.SIDEBAR_WIDTH,
                               border_width=1, border_color=theme.BORDER)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="NULL WALLET",
                     font=ctk.CTkFont("Courier New", 13, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(28, 2))
        ctk.CTkLabel(sidebar, text="Personal Wallet",
                     font=ctk.CTkFont(size=11),
                     text_color=theme.TEXT_MUTED).pack(pady=(0, 28))

        sep = ctk.CTkFrame(sidebar, fg_color=theme.BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=(0, 16))

        for key, label in NAV:
            btn = ctk.CTkButton(
                sidebar, text=label,
                width=theme.SIDEBAR_WIDTH - 24, height=38,
                anchor="w", corner_radius=8,
                fg_color="transparent", text_color=theme.TEXT_DIM,
                hover_color=theme.CARD,
                font=ctk.CTkFont(size=13),
                command=lambda k=key: self.navigate(k),
            )
            btn.pack(padx=12, pady=2)
            self._nav_btns[key] = btn

        # Lock at bottom
        ctk.CTkButton(sidebar, text="Lock Wallet",
                      width=theme.SIDEBAR_WIDTH - 24, height=36,
                      anchor="w", corner_radius=8,
                      fg_color="transparent", text_color=theme.TEXT_MUTED,
                      hover_color=theme.CARD, font=ctk.CTkFont(size=12),
                      command=self._lock).pack(side="bottom", padx=12, pady=20)

        # ── Content area ─────────────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        self.navigate("dashboard")
        self._known_txids: dict = {}
        self._start_receive_poller()

    def _get_view(self, view: str):
        if view in self._views:
            return self._views[view]

        if view == "dashboard":
            from gui.dashboard import DashboardView
            v = DashboardView(self.content, self.wm)
        elif view == "send":
            from gui.send import SendView
            v = SendView(self.content, self.wm)
        elif view == "receive":
            from gui.receive import ReceiveView
            v = ReceiveView(self.content, self.wm)
        elif view == "history":
            from gui.history import HistoryView
            v = HistoryView(self.content, self.wm)
        elif view == "privacy_network":
            from gui.privacy_network import PrivacyNetworkView
            v = PrivacyNetworkView(self.content, self.wm)
        elif view == "settings":
            from gui.settings import SettingsView
            v = SettingsView(self.content, self.wm)
        else:
            raise ValueError(f"Unknown view: {view}")

        self._views[view] = v
        return v

    def navigate(self, view: str):
        for key, btn in self._nav_btns.items():
            if key == view:
                btn.configure(fg_color=theme.CARD, text_color=theme.TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=theme.TEXT_DIM)

        # Hide current view instead of destroying; avoids expensive rebuild.
        if self._current_view is not None:
            try:
                self._current_view.pack_forget()
            except Exception:
                pass

        v = self._get_view(view)
        v.pack(fill="both", expand=True)
        self._current_view = v

        # Trigger lightweight refresh hooks without blocking navigation.
        try:
            if hasattr(v, "_refresh"):
                self.after(1, v._refresh)
            elif hasattr(v, "_load"):
                self.after(1, v._load)
        except Exception:
            pass

    def _start_receive_poller(self):
        CHAINS = [
            ("btc", "BTC", theme.BTC_COLOR),
            ("eth", "ETH", theme.ETH_COLOR),
            ("sol", "SOL", theme.SOL_COLOR),
            ("ton", "TON", theme.TON_COLOR),
        ]

        def _poll():
            for chain_key, symbol, color in CHAINS:
                try:
                    addr = self.wm.get_address(chain_key)
                    if not addr:
                        continue
                    if chain_key == "btc":
                        from wallet.bitcoin import BitcoinWallet
                        txs = BitcoinWallet(addr).get_transactions()
                    elif chain_key == "eth":
                        from wallet.ethereum import EthereumWallet
                        txs = EthereumWallet(addr).get_transactions()
                    elif chain_key == "sol":
                        from wallet.solana_wallet import SolanaWallet
                        txs = SolanaWallet(addr).get_transactions()
                    else:
                        continue

                    if not txs:
                        continue

                    known = self._known_txids.get(chain_key)
                    latest_ids = {t["txid"] for t in txs}

                    if known is None:
                        self._known_txids[chain_key] = latest_ids
                        continue

                    new_txs = [t for t in txs if t["txid"] not in known
                               and (t.get("amount") or 0) > 0]
                    self._known_txids[chain_key] = latest_ids

                    for tx in new_txs:
                        amt = tx.get("amount") or 0
                        def _notify(s=symbol, a=amt, c=color):
                            try:
                                if not self.winfo_exists():
                                    return
                                from gui.toast import show as _toast
                                _toast(self.winfo_toplevel(),
                                       f"{s} Received",
                                       f"+{a:.6f} {s} received",
                                       color=c)
                            except Exception:
                                pass
                        self.after(0, _notify)
                except Exception:
                    continue

        def _loop():
            while True:
                threading.Event().wait(60)
                try:
                    if not self.winfo_exists():
                        break
                except Exception:
                    break
                _poll()

        threading.Thread(target=_loop, daemon=True).start()

    def _lock(self):
        self.wm.lock()
        root = self.winfo_toplevel()
        for w in root.winfo_children():
            w.destroy()
        from gui.login import LoginScreen

        def on_unlock(wm):
            for w in root.winfo_children():
                w.destroy()
            MainLayout(root, wm).pack(fill="both", expand=True)

        LoginScreen(root, on_unlock).pack(fill="both", expand=True)
