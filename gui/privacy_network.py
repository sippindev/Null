import threading
import customtkinter as ctk
from gui import theme


INFO_TEXT = """Some wallets expose more data than necessary when connecting to blockchain services. For example, some wallets connect directly to a single provider, which can see your IP address, the wallet addresses you interact with, and your activity timing. Others request more data than needed or constantly send background requests, which can create a pattern that can be tracked.
Some wallets also log too much information when errors happen, which can include sensitive details like wallet addresses or network data. In other cases, all traffic is forced through one fixed endpoint, which increases the risk of centralized tracking.
Null reduces this exposure by limiting unnecessary requests, keeping logs free of sensitive data, allowing flexible network configuration, and offering optional proxy support to help hide your IP.
Important: Most blockchains are public by design. While Null can help protect your network identity, it does not hide transactions on public blockchains."""


class PrivacyNetworkView(ctk.CTkFrame):
    def __init__(self, parent, wallet_manager):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.wm = wallet_manager

        self._proxy_var = ctk.BooleanVar()
        self._build()
        self._load_state()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=28, pady=(28, 0))

        ctk.CTkLabel(
            hdr,
            text="Privacy & Network",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=theme.TEXT,
        ).pack(side="left")

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=theme.BORDER)
        scroll.pack(fill="both", expand=True, padx=28, pady=(18, 24))

        # Info
        info_card = ctk.CTkFrame(scroll, fg_color=theme.SURFACE, corner_radius=12,
                                 border_width=1, border_color=theme.BORDER)
        info_card.pack(fill="x", pady=(0, 16))

        box = ctk.CTkTextbox(
            info_card,
            height=180,
            fg_color=theme.SURFACE,
            text_color=theme.TEXT_DIM,
            border_width=0,
            wrap="word",
            font=ctk.CTkFont(size=12),
        )
        box.pack(fill="x", padx=16, pady=14)
        box.insert("1.0", INFO_TEXT)
        box.configure(state="disabled")

        # Proxy section
        ctk.CTkLabel(scroll, text="PROXY",
                     font=ctk.CTkFont("Courier New", 11, weight="bold"),
                     text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(0, 10))

        card = ctk.CTkFrame(scroll, fg_color=theme.SURFACE, corner_radius=12,
                            border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=(0, 10))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(16, 10))

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left, text="Use proxy",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=theme.TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Format: hostname:port:username:password",
                     font=ctk.CTkFont(size=11),
                     text_color=theme.TEXT_MUTED).pack(anchor="w")

        self._proxy_switch = ctk.CTkSwitch(
            row, text="", variable=self._proxy_var,
            onvalue=True, offvalue=False,
            button_color=theme.TEXT, button_hover_color=theme.TEXT_MUTED,
            progress_color=theme.SUCCESS,
            command=self._on_proxy_toggle,
        )
        self._proxy_switch.pack(side="right")

        entry_row = ctk.CTkFrame(card, fg_color="transparent")
        entry_row.pack(fill="x", padx=18, pady=(0, 16))

        self._proxy_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="hostname:port:username:password",
            height=36,
            fg_color=theme.CARD,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
            font=ctk.CTkFont(size=12),
        )
        self._proxy_entry.pack(side="left", fill="x", expand=True)

        # Status + test
        status_card = ctk.CTkFrame(scroll, fg_color=theme.SURFACE, corner_radius=12,
                                   border_width=1, border_color=theme.BORDER)
        status_card.pack(fill="x")

        status_row = ctk.CTkFrame(status_card, fg_color="transparent")
        status_row.pack(fill="x", padx=18, pady=14)

        self._status_lbl = ctk.CTkLabel(
            status_row,
            text="Status: Disconnected",
            font=ctk.CTkFont(size=12),
            text_color=theme.TEXT_MUTED,
        )
        self._status_lbl.pack(side="left", fill="x", expand=True)

        self._test_btn = ctk.CTkButton(
            status_row,
            text="Test Connection",
            width=140,
            height=32,
            corner_radius=8,
            fg_color=theme.CARD,
            hover_color=theme.BORDER,
            border_width=1,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
            font=ctk.CTkFont(size=12),
            command=self._test_connection,
        )
        self._test_btn.pack(side="right")

    def _load_state(self):
        from utils.network import is_proxy, get_proxy_raw

        self._proxy_var.set(is_proxy())
        raw = get_proxy_raw()
        if raw:
            try:
                self._proxy_entry.delete(0, "end")
                self._proxy_entry.insert(0, raw)
            except Exception:
                pass

    def _set_status(self, connected: bool, detail: str = ""):
        if connected:
            msg = "Status: Connected" + (f" · {detail}" if detail else "")
            color = theme.SUCCESS
        else:
            msg = "Status: Disconnected" + (f" · {detail}" if detail else "")
            color = theme.ERROR if detail else theme.TEXT_MUTED
        try:
            self._status_lbl.configure(text=msg, text_color=color)
        except Exception:
            pass

    def _on_proxy_toggle(self):
        from utils import network

        if self._proxy_var.get():
            pasted = (self._proxy_entry.get() or "").strip()
            ok, msg = network.set_proxy(pasted, enabled=True)
            if not ok:
                self._proxy_var.set(False)
                self._set_status(False, msg)
                return
            self._set_status(False)
        else:
            network.set_proxy("", enabled=False)
            self._set_status(False)

    def _test_connection(self):
        try:
            self._test_btn.configure(state="disabled", text="Testing…")
            self._set_status(False, "Testing")
        except Exception:
            return

        def _run():
            from utils.network import check_connection

            status = check_connection()

            def _update():
                try:
                    if not self.winfo_exists():
                        return

                    connected = (status.ip and " " not in status.ip and "error" not in status.ip.lower())
                    if status.route == "proxy":
                        self._set_status(bool(connected), f"IP {status.ip}" if connected else status.ip)
                    else:
                        # Proxy isn't active; still show result but mark disconnected per requirement.
                        self._set_status(False, "Proxy not enabled")

                    self._test_btn.configure(state="normal", text="Test Connection")
                except Exception:
                    pass

            self.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()
