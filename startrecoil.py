# startrecoil.py

import sys
import os
from pathlib import Path
from typing import Optional, Type

# 1. Determine Project Root
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 2. Import Configuration
from config import APP_NAME, VERSION, DATA_DIR

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        base_path = sys._MEIPASS  # Where PyInstaller extracts temp files
    except Exception:
        base_path = str(Path(__file__).resolve().parent)
    return os.path.join(base_path, relative_path)


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class WindowManager:

    def __init__(self, root) -> None:
        self.root = root
        self.container = None
        self.current_window: Optional[object] = None

    def setup_container(self) -> None:
        import ttkbootstrap as ttk
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

    def show_window(self, window_class: Type, **kwargs) -> object:
        # Cleanup previous window
        if self.current_window is not None:
            if hasattr(self.current_window, 'cleanup'):
                self.current_window.cleanup()

        # Clear container
        if self.container is not None:
            for widget in self.container.winfo_children():
                widget.destroy()

        # Create and display new window
        self.current_window = window_class(self.container, **kwargs)
        return self.current_window


def main() -> None:
    print(f"Starting {APP_NAME} {VERSION}...")

    # Ensure directories exist
    ensure_directories()

    # Import GUI modules
    import ttkbootstrap as ttk
    from gui.main_window import RecoilCalculatorApp

    # Create the root window
    root = ttk.Tk()
    root.title(APP_NAME)

    # Set the application icon (Only after root is created)
    try:
        from PIL import ImageTk
        icon_path = get_resource_path('gui/bcalcrecoilicon.png')
        if os.path.exists(icon_path):
            icon_img = ImageTk.PhotoImage(file=icon_path)
            root.iconphoto(True, icon_img)
    except Exception as e:
        print(f"Warning: Could not load app icon: {e}")

    # Initialize window manager
    manager = WindowManager(root)
    manager.setup_container()

    # Display the main application window
    manager.show_window(RecoilCalculatorApp)

    # Start the application loop
    root.mainloop()


if __name__ == "__main__":
    main()

