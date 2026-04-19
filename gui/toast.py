import customtkinter as ctk
from gui import theme


def show(root, title: str, message: str, color: str = theme.SUCCESS, duration_ms: int = 4000):
    """Show a toast notification in the bottom-right corner of root."""
    toast = ctk.CTkToplevel(root)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.configure(fg_color=theme.CARD)

    frame = ctk.CTkFrame(toast, fg_color=theme.CARD, corner_radius=10,
                         border_width=1, border_color=color)
    frame.pack(padx=1, pady=1)

    bar = ctk.CTkFrame(frame, fg_color=color, width=4, corner_radius=0)
    bar.pack(side="left", fill="y")

    content = ctk.CTkFrame(frame, fg_color="transparent")
    content.pack(side="left", padx=(12, 16), pady=12)

    ctk.CTkLabel(content, text=title,
                 font=ctk.CTkFont(size=13, weight="bold"),
                 text_color=theme.TEXT).pack(anchor="w")
    ctk.CTkLabel(content, text=message,
                 font=ctk.CTkFont(size=11),
                 text_color=theme.TEXT_MUTED,
                 wraplength=240).pack(anchor="w")

    def _place():
        toast.update_idletasks()
        w = toast.winfo_width()
        h = toast.winfo_height()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        toast.geometry(f"+{sw - w - 24}+{sh - h - 60}")

    toast.after(10, _place)
    toast.after(duration_ms, lambda: toast.destroy() if toast.winfo_exists() else None)
