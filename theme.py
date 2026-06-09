#theme.py

from ttkbootstrap.constants import *
import ttkbootstrap as tb
import tkinter as tk
from tkinter import ttk


COLOR_BG_FRAME = "#FFFFFF"
COLOR_LABEL = "#333333"
COLOR_WHITE = "#FFFFFF"
COLOR_GRAY = "#D3D3D3"
COLOR_ERROR_BG = "#FFCDD2"
COLOR_ERROR_TEXT = "#D32F2F"
COLOR_UNIT = "#999999"
COLOR_HEADER_BG = "#F5F5F5"
COLOR_SUCCESS = "#4CAF50"
COLOR_WARNING = "#FF9800"

COLOR_INFO_BG = "#E3F2FD"
COLOR_INFO_FG = "#1976D2"
COLOR_WARNING_BG = "#FFF3E0"
COLOR_WARNING_FG = "#F57C00"


FONT_FAMILY = "Roboto"
LABEL_FONT_SIZE = 12
UNIT_FONT_SIZE = 10
TITLE_FONT_SIZE = 16
HEADER_FONT_SIZE = 13
SMALL_FONT_SIZE = 10
BUTTON_FONT_SIZE = 12
DIALOG_FONT_SIZE = 10


PADDING_SM = 5
PADDING_MD = 10
PADDING_LG = 20
INPUT_WIDTH_CHARS = 15
LABEL_WIDTH_CHARS = 18
BUTTON_PADDING = (15, 5)

COMPARISON_LIMIT = 4

def setup_styles(style: tb.Style):
    style.configure("TEntry", font=(FONT_FAMILY, LABEL_FONT_SIZE))
    style.configure("TCombobox", font=(FONT_FAMILY, LABEL_FONT_SIZE))
    style.configure("TButton", font=(FONT_FAMILY, BUTTON_FONT_SIZE))
    style.configure("TFrame", background=COLOR_BG_FRAME)
    style.configure("TLabelframe", background=COLOR_BG_FRAME)
    style.configure("TLabelframe.Label", font=(FONT_FAMILY, HEADER_FONT_SIZE, "bold"))

    style.configure("CustomFrame.TFrame", background=COLOR_BG_FRAME)

    style.configure("CustomLabel.TLabel", foreground=COLOR_LABEL, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, LABEL_FONT_SIZE))
    style.configure("Unit.TLabel", foreground=COLOR_UNIT, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, UNIT_FONT_SIZE))
    style.configure("Title.TLabel", foreground=COLOR_LABEL, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, TITLE_FONT_SIZE, "bold"))
    style.configure("Header.TLabel", foreground=COLOR_LABEL, background=COLOR_HEADER_BG,
                    font=(FONT_FAMILY, LABEL_FONT_SIZE, "bold"))
    style.configure("Section.TLabel", foreground=COLOR_LABEL, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, HEADER_FONT_SIZE, "bold"))
    style.configure("Small.TLabel", foreground=COLOR_LABEL, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, SMALL_FONT_SIZE))
    style.configure("Data.TLabel", foreground=COLOR_LABEL, background=COLOR_WHITE,
                    font=(FONT_FAMILY, SMALL_FONT_SIZE))
    style.configure("DataHeader.TLabel", foreground=COLOR_LABEL, background=COLOR_GRAY,
                    font=(FONT_FAMILY, SMALL_FONT_SIZE, "bold"))
    style.configure("White.TCombobox", fieldbackground=COLOR_WHITE, foreground="black",
                    font=(FONT_FAMILY, LABEL_FONT_SIZE))
    style.configure("White.TEntry", fieldbackground=COLOR_WHITE, foreground="black",
                    font=(FONT_FAMILY, LABEL_FONT_SIZE))
    style.configure("Gray.TEntry", fieldbackground=COLOR_GRAY, foreground="black",
                    font=(FONT_FAMILY, LABEL_FONT_SIZE), state="readonly")
    style.configure("Error.TEntry", fieldbackground=COLOR_ERROR_BG, foreground="black",
                    font=(FONT_FAMILY, LABEL_FONT_SIZE))
    style.configure("Error.TLabel", foreground=COLOR_ERROR_TEXT, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, UNIT_FONT_SIZE))
    style.configure("Success.TLabel", foreground=COLOR_SUCCESS, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, LABEL_FONT_SIZE))
    style.configure("Warning.TLabel", foreground=COLOR_WARNING, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, LABEL_FONT_SIZE))
    style.configure("Bold.TLabel", foreground=COLOR_LABEL, background=COLOR_BG_FRAME,
                    font=(FONT_FAMILY, SMALL_FONT_SIZE, "bold"))

    style.configure("Dialog.TFrame", background=COLOR_BG_FRAME)
    style.configure("Dialog.TLabel", background=COLOR_BG_FRAME,
                    foreground=COLOR_LABEL, font=(FONT_FAMILY, DIALOG_FONT_SIZE))
    style.configure("Dialog.TButton", font=(FONT_FAMILY, DIALOG_FONT_SIZE))


def get_style_for_field(validation_passed: bool = True, is_readonly: bool = False) -> str:
    if is_readonly:
        return "Gray.TEntry"
    elif not validation_passed:
        return "Error.TEntry"
    else:
        return "White.TEntry"

def show_themable_dialog(parent, title, message, kind="info"):
    dlg = tk.Toplevel(parent)
    dlg.transient(parent)
    dlg.grab_set()
    dlg.title(title)
    dlg.resizable(False, False)
    try:
        dlg.iconbitmap("")
    except Exception:
        pass

    container = ttk.Frame(dlg, padding=PADDING_MD, style="Dialog.TFrame")
    container.pack(fill="both", expand=True)

    ttk.Label(container, text=message, wraplength=460, justify="left",
              style="Dialog.TLabel").pack(fill="both", expand=True, pady=(0, PADDING_MD))

    ttk.Button(container, text="OK", command=dlg.destroy, style="TButton").pack(anchor="e")

    parent.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dlg.winfo_reqwidth()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dlg.winfo_reqheight()) // 2
    dlg.geometry(f"+{x}+{y}")

    parent.wait_window(dlg)







