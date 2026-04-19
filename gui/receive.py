import customtkinter as ctk
from gui import theme

CHAINS = [
    ("btc", "Bitcoin",  "BTC", theme.BTC_COLOR),
    ("eth", "Ethereum", "ETH", theme.ETH_COLOR),
    ("sol", "Solana",   "SOL", theme.SOL_COLOR),
    ("ton", "TON",      "TON", theme.TON_COLOR),
]


class ReceiveView(ctk.CTkFrame):
    def __init__(self, parent, wallet_manager):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.wm = wallet_manager
        self._selected = "btc"
        self._chain_btns: dict = {}
        self._qr_ref = None
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Receive",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=theme.TEXT).pack(anchor="w", padx=28, pady=(28, 20))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # ── Left panel ────────────────────────────────────────────────
        left = ctk.CTkFrame(body, fg_color=theme.SURFACE, corner_radius=12,
                            border_width=1, border_color=theme.BORDER, width=240)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="SELECT CHAIN",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=theme.TEXT_DIM).pack(anchor="w", padx=16, pady=(18, 10))

        for chain_key, name, symbol, color in CHAINS:
            btn = ctk.CTkButton(
                left, text=f"{name}  ({symbol})",
                width=208, height=38, anchor="w", corner_radius=8,
                fg_color=theme.CARD, text_color=theme.TEXT_DIM,
                hover_color=theme.BORDER,
                font=ctk.CTkFont(size=13),
                command=lambda k=chain_key: self._select(k),
            )
            btn.pack(padx=16, pady=3)
            self._chain_btns[chain_key] = btn

        sep = ctk.CTkFrame(left, fg_color=theme.BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(left, text="ADDRESS",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=theme.TEXT_DIM).pack(anchor="w", padx=16, pady=(0, 6))

        self.addr_lbl = ctk.CTkLabel(left, text="",
                                      font=ctk.CTkFont("Courier New", 10),
                                      text_color=theme.TEXT, wraplength=200)
        self.addr_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        self.copy_btn = ctk.CTkButton(left, text="Copy Address",
                                       width=208, height=36, corner_radius=8,
                                       fg_color=theme.BORDER, text_color=theme.TEXT,
                                       hover_color=theme.CARD, font=ctk.CTkFont(size=12),
                                       command=self._copy)
        self.copy_btn.pack(padx=16, pady=(0, 18))

        # ── Right panel (QR) ─────────────────────────────────────────
        right = ctk.CTkFrame(body, fg_color=theme.SURFACE, corner_radius=12,
                             border_width=1, border_color=theme.BORDER)
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="QR CODE",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=theme.TEXT_DIM).pack(pady=(18, 12))

        self.qr_lbl = ctk.CTkLabel(right, text="", image=None)
        self.qr_lbl.pack(expand=True)

        self._select("btc")

    def _select(self, chain_key: str):
        self._selected = chain_key
        _, _, _, sel_color = next(c for c in CHAINS if c[0] == chain_key)

        for k, btn in self._chain_btns.items():
            _, _, _, color = next(c for c in CHAINS if c[0] == k)
            if k == chain_key:
                btn.configure(fg_color=theme.CARD, text_color=theme.TEXT,
                              border_width=1, border_color=sel_color)
            else:
                btn.configure(fg_color="transparent", text_color=theme.TEXT_DIM,
                              border_width=0)

        addr = self.wm.get_address(chain_key)
        self.addr_lbl.configure(text=addr)
        self._gen_qr(addr)

    def _gen_qr(self, data: str):
        try:
            import qrcode
            from PIL import Image as PILImage

            qr = qrcode.QRCode(version=1, box_size=7, border=2,
                               error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="white", back_color="#141414")
            img = img.resize((230, 230), PILImage.NEAREST)

            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(230, 230))
            self._qr_ref = ctk_img
            self.qr_lbl.configure(image=ctk_img, text="")
        except ImportError:
            self.qr_lbl.configure(text="pip install qrcode Pillow\nto show QR code",
                                   text_color=theme.TEXT_DIM, image=None)
        except Exception as e:
            self.qr_lbl.configure(text=f"QR error:\n{e}",
                                   text_color=theme.ERROR, image=None)

    def _copy(self):
        addr = self.wm.get_address(self._selected)
        self.clipboard_clear()
        self.clipboard_append(addr)
        self.copy_btn.configure(text="Copied ✓", text_color=theme.SUCCESS)
        self.after(1800, lambda: self.copy_btn.configure(text="Copy Address",
                                                          text_color=theme.TEXT))
