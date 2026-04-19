import threading
import customtkinter as ctk
from gui import theme


class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, wallet_manager):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.wm = wallet_manager
        self._tor_var = ctk.BooleanVar()
        self._build()
        self._load_tor_state()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(28, 0))
        ctk.CTkLabel(header, text="Settings",
                     font=ctk.CTkFont("Courier New", 22, weight="bold"),
                     text_color=theme.TEXT).pack(anchor="w")
        ctk.CTkLabel(header, text="Configure wallet behaviour",
                     font=ctk.CTkFont(size=12),
                     text_color=theme.TEXT_MUTED).pack(anchor="w")

        ctk.CTkFrame(self, fg_color=theme.BORDER, height=1).pack(
            fill="x", padx=32, pady=(18, 24))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=theme.BORDER)
        scroll.pack(fill="both", expand=True, padx=32, pady=(0, 24))

        self._build_tor_section(scroll)
        self._build_sep(scroll)
        self._build_security_section(scroll)
        self._build_sep(scroll)
        self._build_about_section(scroll)

    # ── Tor ─────────────────────────────────────────────────────────────────

    def _build_tor_section(self, parent):
        ctk.CTkLabel(parent, text="TOR NETWORK",
                     font=ctk.CTkFont("Courier New", 11, weight="bold"),
                     text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(0, 12))

        card = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=10,
                            border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(14, 10))

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left, text="Route through Tor",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=theme.TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="SOCKS5 proxy on 127.0.0.1:9050",
                     font=ctk.CTkFont(size=11),
                     text_color=theme.TEXT_MUTED).pack(anchor="w")

        self._tor_switch = ctk.CTkSwitch(
            row, text="", variable=self._tor_var,
            onvalue=True, offvalue=False,
            button_color=theme.TEXT, button_hover_color=theme.TEXT_MUTED,
            progress_color=theme.SUCCESS,
            command=self._on_tor_toggle,
        )
        self._tor_switch.pack(side="right")

        # Port row
        port_row = ctk.CTkFrame(card, fg_color="transparent")
        port_row.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkLabel(port_row, text="Proxy port:",
                     font=ctk.CTkFont(size=12),
                     text_color=theme.TEXT_MUTED).pack(side="left")
        self._port_entry = ctk.CTkEntry(
            port_row, width=80, height=28,
            fg_color=theme.SURFACE, border_color=theme.BORDER,
            text_color=theme.TEXT, font=ctk.CTkFont(size=12),
        )
        self._port_entry.insert(0, "9050")
        self._port_entry.pack(side="left", padx=(8, 0))

        # Status row
        status_card = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=10,
                                   border_width=1, border_color=theme.BORDER)
        status_card.pack(fill="x", pady=(0, 8))

        status_row = ctk.CTkFrame(status_card, fg_color="transparent")
        status_row.pack(fill="x", padx=18, pady=14)

        self._status_lbl = ctk.CTkLabel(
            status_row, text="Status: not tested",
            font=ctk.CTkFont(size=12), text_color=theme.TEXT_MUTED,
        )
        self._status_lbl.pack(side="left", fill="x", expand=True)

        self._test_btn = ctk.CTkButton(
            status_row, text="Test Connection",
            width=130, height=32, corner_radius=8,
            fg_color=theme.SURFACE, hover_color=theme.CARD,
            border_width=1, border_color=theme.BORDER,
            text_color=theme.TEXT, font=ctk.CTkFont(size=12),
            command=self._test_connection,
        )
        self._test_btn.pack(side="right")

    # ── Security ────────────────────────────────────────────────────────────

    def _build_security_section(self, parent):
        ctk.CTkLabel(parent, text="SECURITY",
                     font=ctk.CTkFont("Courier New", 11, weight="bold"),
                     text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(0, 12))

        card = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=10,
                            border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=(0, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=14)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left, text="Change Password",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=theme.TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Wallet file is re-encrypted with your new password",
                     font=ctk.CTkFont(size=11),
                     text_color=theme.TEXT_MUTED).pack(anchor="w")

        ctk.CTkButton(
            inner, text="Change",
            width=90, height=32, corner_radius=8,
            fg_color=theme.SURFACE, hover_color=theme.CARD,
            border_width=1, border_color=theme.BORDER,
            text_color=theme.TEXT, font=ctk.CTkFont(size=12),
            command=self._open_change_password,
        ).pack(side="right")

    # ── About ───────────────────────────────────────────────────────────────

    def _build_about_section(self, parent):
        ctk.CTkLabel(parent, text="ABOUT",
                     font=ctk.CTkFont("Courier New", 11, weight="bold"),
                     text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(0, 12))

        card = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=10,
                            border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=(0, 8))

        rows = [
            ("Application", "Null Wallet"),
            ("Version",     "1.0.0"),
            ("Chains",      "BTC · ETH · SOL · TON"),
            ("Encryption",  "Fernet + scrypt (new) / PBKDF2 (legacy)"),
        ]
        for i, (k, v) in enumerate(rows):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=(10 if i == 0 else 4, 10 if i == len(rows) - 1 else 4))
            ctk.CTkLabel(row, text=k, width=150, anchor="w",
                         font=ctk.CTkFont(size=12), text_color=theme.TEXT_MUTED).pack(side="left")
            ctk.CTkLabel(row, text=v, anchor="w",
                         font=ctk.CTkFont(size=12), text_color=theme.TEXT).pack(side="left")

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _build_sep(self, parent):
        ctk.CTkFrame(parent, fg_color=theme.BORDER, height=1).pack(fill="x", pady=20)

    def _load_tor_state(self):
        from utils.network import is_tor
        self._tor_var.set(is_tor())

    def _on_tor_toggle(self):
        from utils import network
        try:
            port = int(self._port_entry.get().strip())
        except ValueError:
            port = 9050
        network.set_tor(self._tor_var.get(), port)

    def _test_connection(self):
        self._test_btn.configure(state="disabled", text="Testing…")
        self._status_lbl.configure(text="Status: connecting…", text_color=theme.TEXT_MUTED)

        def _run():
            from utils.network import check_connection
            status = check_connection()

            def _update():
                try:
                    if not self.winfo_exists():
                        return

                    if status.route == "tor" and status.is_tor is True:
                        self._status_lbl.configure(text=f"Status: Tor active · IP {status.ip}", text_color=theme.SUCCESS)
                    elif status.route == "tor":
                        self._status_lbl.configure(text=f"Status: Tor selected · {status.ip}", text_color=theme.WARNING)
                    else:
                        self._status_lbl.configure(text=f"Status: Not using Tor · IP {status.ip}", text_color=theme.ERROR)

                    self._test_btn.configure(state="normal", text="Test Connection")
                except Exception:
                    pass

            self.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()

    def _open_change_password(self):
        dialog = _ChangePasswordDialog(self)
        dialog.grab_set()


class _ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.wm = parent.wm
        self.title("Change Password")
        self.geometry("420x320")
        self.resizable(False, False)
        self.configure(fg_color=theme.BG)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Change Password",
                     font=ctk.CTkFont("Courier New", 16, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(24, 4))
        ctk.CTkLabel(self, text="Enter current password then choose a new one",
                     font=ctk.CTkFont(size=11), text_color=theme.TEXT_MUTED).pack(pady=(0, 20))

        def _field(label):
            ctk.CTkLabel(self, text=label, anchor="w",
                         font=ctk.CTkFont(size=12), text_color=theme.TEXT_MUTED).pack(
                fill="x", padx=32)
            e = ctk.CTkEntry(self, show="•", height=36,
                             fg_color=theme.SURFACE, border_color=theme.BORDER,
                             text_color=theme.TEXT, font=ctk.CTkFont(size=13))
            e.pack(fill="x", padx=32, pady=(4, 12))
            return e

        self._cur = _field("Current password")
        self._new1 = _field("New password")
        self._new2 = _field("Confirm new password")

        self._msg = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color=theme.ERROR)
        self._msg.pack()

        ctk.CTkButton(self, text="Update Password",
                      height=38, corner_radius=8,
                      fg_color=theme.TEXT, text_color=theme.BG,
                      hover_color=theme.TEXT_MUTED,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self._submit).pack(fill="x", padx=32, pady=(8, 0))

    def _submit(self):
        cur = self._cur.get()
        new1 = self._new1.get()
        new2 = self._new2.get()

        if not cur or not new1:
            self._msg.configure(text="All fields are required.")
            return
        if new1 != new2:
            self._msg.configure(text="New passwords do not match.")
            return
        if len(new1) < 12:
            self._msg.configure(text="Password must be at least 12 characters.")
            return

        ok, err = self.wm.change_password(cur, new1)
        if ok:
            self._msg.configure(text="Password updated.", text_color=theme.SUCCESS)
            self.after(1200, self.destroy)
        else:
            self._msg.configure(text=err or "Incorrect current password.", text_color=theme.ERROR)
