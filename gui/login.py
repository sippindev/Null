import customtkinter as ctk
from gui import theme
from wallet.manager import WalletManager
from typing import Callable


class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, on_unlock: Callable):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.on_unlock = on_unlock
        self.wm = WalletManager()
        self._build()

    def _build(self):
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(center, text="NULL WALLET",
                     font=ctk.CTkFont("Courier New", 30, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(0, 4))
        ctk.CTkLabel(center, text="BTC  ·  ETH  ·  SOL  ·  TON",
                     font=ctk.CTkFont("Courier New", 12),
                     text_color=theme.TEXT_DIM).pack(pady=(0, 36))

        card = ctk.CTkFrame(center, fg_color=theme.SURFACE, corner_radius=14,
                            border_width=1, border_color=theme.BORDER)
        card.pack()

        if self.wm.wallet_exists():
            self._unlock_form(card)
        else:
            self._create_form(card)

    def _unlock_form(self, parent):
        ctk.CTkLabel(parent, text="Welcome back",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(24, 4))
        ctk.CTkLabel(parent, text="Enter your password to unlock",
                     font=ctk.CTkFont(size=13), text_color=theme.TEXT_DIM).pack(pady=(0, 20))

        self.pw_entry = ctk.CTkEntry(parent, placeholder_text="Password", show="●",
                                     width=300, height=42, fg_color=theme.CARD,
                                     border_color=theme.BORDER, text_color=theme.TEXT,
                                     font=ctk.CTkFont(size=14))
        self.pw_entry.pack(padx=32, pady=(0, 8))
        self.pw_entry.bind("<Return>", lambda _: self._do_unlock())
        self.pw_entry.focus()

        self.status = ctk.CTkLabel(parent, text="", text_color=theme.ERROR,
                                   font=ctk.CTkFont(size=12))
        self.status.pack(pady=(0, 8))

        ctk.CTkButton(parent, text="Unlock", width=300, height=42,
                      fg_color=theme.TEXT, text_color=theme.BG, hover_color="#D0D0D0",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._do_unlock).pack(padx=32, pady=(0, 8))

        ctk.CTkButton(parent, text="Import different wallet",
                      width=300, height=34, fg_color="transparent",
                      text_color=theme.TEXT_DIM, hover_color=theme.CARD,
                      font=ctk.CTkFont(size=12),
                      command=self._show_import).pack(padx=32, pady=(0, 20))

    def _create_form(self, parent):
        ctk.CTkLabel(parent, text="Create Wallet",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(24, 4))
        ctk.CTkLabel(parent, text="Set a strong password (12+ characters)",
                     font=ctk.CTkFont(size=13), text_color=theme.TEXT_DIM).pack(pady=(0, 20))

        self.pw_entry = ctk.CTkEntry(parent, placeholder_text="Password", show="●",
                                     width=300, height=42, fg_color=theme.CARD,
                                     border_color=theme.BORDER, text_color=theme.TEXT,
                                     font=ctk.CTkFont(size=14))
        self.pw_entry.pack(padx=32, pady=(0, 8))
        self.pw_entry.focus()

        self.pw2_entry = ctk.CTkEntry(parent, placeholder_text="Confirm password", show="●",
                                      width=300, height=42, fg_color=theme.CARD,
                                      border_color=theme.BORDER, text_color=theme.TEXT,
                                      font=ctk.CTkFont(size=14))
        self.pw2_entry.pack(padx=32, pady=(0, 8))
        self.pw2_entry.bind("<Return>", lambda _: self._do_create())

        self.status = ctk.CTkLabel(parent, text="", text_color=theme.ERROR,
                                   font=ctk.CTkFont(size=12))
        self.status.pack(pady=(0, 8))

        ctk.CTkButton(parent, text="Create New Wallet", width=300, height=42,
                      fg_color=theme.TEXT, text_color=theme.BG, hover_color="#D0D0D0",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._do_create).pack(padx=32, pady=(0, 8))

        ctk.CTkButton(parent, text="Import existing wallet",
                      width=300, height=34, fg_color="transparent",
                      text_color=theme.TEXT_DIM, hover_color=theme.CARD,
                      font=ctk.CTkFont(size=12),
                      command=self._show_import).pack(padx=32, pady=(0, 20))

    def _do_unlock(self):
        pw = self.pw_entry.get()
        if not pw:
            self.status.configure(text="Enter your password")
            return
        self.status.configure(text="Unlocking…", text_color=theme.TEXT_DIM)
        self.update()
        if self.wm.unlock(pw):
            self.on_unlock(self.wm)
        else:
            self.status.configure(text="Incorrect password", text_color=theme.ERROR)
            self.pw_entry.delete(0, "end")

    def _do_create(self):
        pw = self.pw_entry.get()
        pw2 = self.pw2_entry.get()
        if len(pw) < 12:
            self.status.configure(text="Password must be at least 12 characters")
            return
        if pw != pw2:
            self.status.configure(text="Passwords don't match")
            return
        self.status.configure(text="Generating wallet…", text_color=theme.TEXT_DIM)
        self.update()
        mnemonic = self.wm.create_wallet(pw)
        self._show_mnemonic(mnemonic)

    def _show_import(self):
        self._rebuild_with(self._import_form)

    def _rebuild_with(self, builder):
        for w in self.winfo_children():
            w.destroy()
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(center, text="NULL WALLET",
                     font=ctk.CTkFont("Courier New", 30, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(0, 4))
        ctk.CTkLabel(center, text="BTC  ·  ETH  ·  SOL  ·  TON",
                     font=ctk.CTkFont("Courier New", 12),
                     text_color=theme.TEXT_DIM).pack(pady=(0, 36))
        card = ctk.CTkFrame(center, fg_color=theme.SURFACE, corner_radius=14,
                            border_width=1, border_color=theme.BORDER)
        card.pack()
        builder(card)

    def _import_form(self, parent):
        ctk.CTkLabel(parent, text="Import Wallet",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(24, 4))
        ctk.CTkLabel(parent, text="Enter your 12-word seed phrase",
                     font=ctk.CTkFont(size=13), text_color=theme.TEXT_DIM).pack(pady=(0, 16))

        mnemonic_box = ctk.CTkTextbox(parent, width=320, height=80,
                                       fg_color=theme.CARD, border_color=theme.BORDER,
                                       text_color=theme.TEXT, font=ctk.CTkFont(size=13))
        mnemonic_box.pack(padx=32, pady=(0, 8))

        pw_entry = ctk.CTkEntry(parent, placeholder_text="New password", show="●",
                                width=320, height=42, fg_color=theme.CARD,
                                border_color=theme.BORDER, text_color=theme.TEXT)
        pw_entry.pack(padx=32, pady=(0, 8))

        status = ctk.CTkLabel(parent, text="", text_color=theme.ERROR, font=ctk.CTkFont(size=12))
        status.pack(pady=(0, 8))

        def do_import():
            words = mnemonic_box.get("1.0", "end").strip()
            pw = pw_entry.get()
            if not words:
                status.configure(text="Enter seed phrase")
                return
            if len(pw) < 12:
                status.configure(text="Password must be at least 12 characters")
                return
            status.configure(text="Importing…", text_color=theme.TEXT_DIM)
            self.update()
            if self.wm.import_wallet(words, pw):
                self.on_unlock(self.wm)
            else:
                status.configure(text="Invalid seed phrase", text_color=theme.ERROR)

        ctk.CTkButton(parent, text="Import", width=320, height=42,
                      fg_color=theme.TEXT, text_color=theme.BG, hover_color="#D0D0D0",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=do_import).pack(padx=32, pady=(0, 8))

        ctk.CTkButton(parent, text="← Back", width=320, height=34,
                      fg_color="transparent", text_color=theme.TEXT_DIM, hover_color=theme.CARD,
                      font=ctk.CTkFont(size=12),
                      command=self._rebuild_main).pack(padx=32, pady=(0, 20))

    def _rebuild_main(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _show_mnemonic(self, mnemonic: str):
        for w in self.winfo_children():
            w.destroy()

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(outer, text="NULL WALLET",
                     font=ctk.CTkFont("Courier New", 26, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(0, 28))

        card = ctk.CTkFrame(outer, fg_color=theme.SURFACE, corner_radius=14,
                            border_width=1, border_color=theme.BORDER)
        card.pack()

        ctk.CTkLabel(card, text="Save Your Seed Phrase",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=theme.TEXT).pack(pady=(24, 4))
        ctk.CTkLabel(card, text="Write these 12 words down. NEVER share them with anyone.",
                     font=ctk.CTkFont(size=12), text_color=theme.ERROR).pack(pady=(0, 20))

        words = mnemonic.split()
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(padx=24, pady=(0, 20))

        for i, word in enumerate(words):
            row, col = divmod(i, 4)
            cell = ctk.CTkFrame(grid, fg_color=theme.CARD, corner_radius=6,
                                border_width=1, border_color=theme.BORDER)
            cell.grid(row=row, column=col, padx=4, pady=4, ipadx=6, ipady=4)
            ctk.CTkLabel(cell, text=f"{i+1}.", font=ctk.CTkFont(size=10),
                         text_color=theme.TEXT_DIM, width=18).pack(side="left", padx=(4, 0))
            ctk.CTkLabel(cell, text=word, font=ctk.CTkFont("Courier New", 13, weight="bold"),
                         text_color=theme.TEXT, width=72).pack(side="left", padx=(2, 6))

        ctk.CTkButton(card, text="I've saved my seed phrase  →",
                      width=380, height=44,
                      fg_color=theme.TEXT, text_color=theme.BG, hover_color="#D0D0D0",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=lambda: self.on_unlock(self.wm)).pack(padx=32, pady=(4, 24))
