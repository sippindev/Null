import customtkinter as ctk
from gui import theme

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Null Wallet")
        self.geometry("1020x660")
        self.minsize(900, 580)
        self.configure(fg_color=theme.BG)
        self._show_login()

    def _show_login(self):
        self._clear()
        from gui.login import LoginScreen
        LoginScreen(self, self._on_unlocked).pack(fill="both", expand=True)

    def _on_unlocked(self, wallet_manager):
        self._clear()
        from gui.main_layout import MainLayout
        MainLayout(self, wallet_manager).pack(fill="both", expand=True)

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()
