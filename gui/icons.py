"""
Programmatically drawn crypto logos using PIL.
Returns CTkImage instances ready for use in labels/buttons.
"""
from PIL import Image, ImageDraw, ImageFont
import customtkinter as ctk

_cache: dict = {}


def _hex(color: str) -> tuple:
    c = color.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))


def _circle_icon(bg_hex: str, symbol: str, size: int = 40) -> ctk.CTkImage:
    key = (bg_hex, symbol, size)
    if key in _cache:
        return _cache[key]

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Circle background
    draw.ellipse([0, 0, size - 1, size - 1], fill=_hex(bg_hex) + (255,))

    # Try to use a bold system font
    font = None
    font_size = int(size * 0.38)
    for fname in ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "verdanab.ttf"]:
        try:
            font = ImageFont.truetype(fname, font_size)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    # Center text
    bbox = draw.textbbox((0, 0), symbol, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1]
    draw.text((x, y), symbol, fill=(255, 255, 255, 255), font=font)

    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    _cache[key] = ctk_img
    return ctk_img


def btc(size: int = 40) -> ctk.CTkImage:
    return _circle_icon("#F7931A", "₿", size)

def eth(size: int = 40) -> ctk.CTkImage:
    return _circle_icon("#627EEA", "Ξ", size)

def sol(size: int = 40) -> ctk.CTkImage:
    return _circle_icon("#9945FF", "◎", size)

def ton(size: int = 40) -> ctk.CTkImage:
    return _circle_icon("#0098EA", "💎", size)

def xmr(size: int = 40) -> ctk.CTkImage:
    return _circle_icon("#FF6600", "ɱ", size)

ICONS = {"btc": btc, "eth": eth, "sol": sol, "ton": ton, "xmr": xmr}

def get(chain: str, size: int = 40) -> ctk.CTkImage:
    return ICONS.get(chain, lambda s: _circle_icon("#555555", "?", s))(size)
