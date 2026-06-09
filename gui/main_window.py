# gui/main_window.py


import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from typing import Dict, Optional, List, Any
from recoil_math import calculate_recoil
from db_manager import init_db, save_calculation, get_history
from theme import setup_styles, COLOR_LABEL, COLOR_UNIT, COLOR_SUCCESS, FONT_FAMILY, PADDING_MD, show_themable_dialog
from tkinter import messagebox
import os
from PIL import Image, ImageTk


from config import (
    FIREARM_CLASSES,
    ACTION_MODIFIERS,
    MUZZLE_DEVICES,
    FIT_PENALTIES,
    CARTRIDGE_DEFAULTS,
    firearm_classes_display,
    muzzle_devices_display,
    CLASS_KEY_MAP,
    lop_display,
    comb_display,
    buttplate_display
)

class RecoilCalculatorApp:
    def __init__(self, container):
        self.container = container


        self.root = container.winfo_toplevel()
        self.root.title("Bcalc Recoil Calculator")
        self.root.geometry("1100x675")

        # Initialize Database
        init_db()

        # Setup Styles
        style = ttk.Style()
        style.theme_use("litera")
        setup_styles(style)

        # State Variables
        self.armammo_name_var = tk.StringVar(value="")
        self.cartridge_var = tk.StringVar()
        self.calc_counter = 0
        self.combo_history = None

        # 1. Firearm Class: Display Name (from CSV list)
        self.firearm_class_var = tk.StringVar(value=firearm_classes_display[0] if firearm_classes_display else "Rifle: Standard")

        # 2. Action Type: Internal Key (e.g., "bolt_action")

        default_class_key = CLASS_KEY_MAP.get(self.firearm_class_var.get(), "rifle_standard")
        valid_actions_list = FIREARM_CLASSES.get(default_class_key, {}).get("valid_actions", [])

        default_action_key = valid_actions_list[0] if valid_actions_list else "bolt_action"
        self.action_type_var = tk.StringVar(value=default_action_key)

        # 3. Muzzle Device: Display Name (from CSV list)
        self.muzzle_device_var = tk.StringVar(value=muzzle_devices_display[0] if muzzle_devices_display else "None")

        # 4. Fit Factors: Display Labels

        self.lop_fit_var = tk.StringVar(value=lop_display[0] if lop_display else "just right")
        self.comb_fit_var = tk.StringVar(value=comb_display[0] if comb_display else "just right")
        self.buttplate_fit_var = tk.StringVar(value=buttplate_display[0] if buttplate_display else "hard")

        # Storage for Entry widgets to access values later
        self.entries: Dict[str, ttk.Entry] = {}
        self.calculated_result: Optional[Dict[str, Any]] = None

        # History cache
        self.history_data: List[Dict[str, Any]] = []

        # --- Load Icon for Results Section
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "bcalcrecoilicon.png")

        if not os.path.exists(icon_path):
            print(f"Warning: Icon file not found: {icon_path}")
            self.results_icon = None
        else:
            try:

                img = Image.open(icon_path)
                img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.results_icon = photo  # Keep reference to prevent garbage collection
            except Exception as e:
                print(f"Failed to load icon: {e}")
                self.results_icon = None
    # ---------------------------------------------------------------

        # Create Layout - bind to container not root
        self.create_widgets(container)
        self.update_action_dropdown()

        # Bind Cartridge Change
        self.setup_cartridge_logic()

        # populate drop-down box
        self._refresh_history_dropdown()

    def show_dialog(self, title: str, message: str):

        try:
            if hasattr(self, "_app_menu"):
                try:
                    self._app_menu.unpost()
                except Exception:
                    pass
        finally:
            messagebox.showinfo(title, message)

    def create_widgets(self, container):
        """Create the main layout with Input (Left) and Output (Right) panels."""

        # Main Container - FIX: use container parameter
        main_container = ttk.Frame(container, padding=15)
        main_container.pack(fill=BOTH, expand=True)

        # Grid Layout: Left (Input) | Right (Output)
        main_container.columnconfigure(0, weight=2)
        main_container.columnconfigure(1, weight=2)

        # --- LEFT COLUMN: INPUT FORM ---
        input_frame = ttk.LabelFrame(main_container, text="Input Parameters")
        input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        row = 0

        # 1. Unique Name & History Dropdown (Row 0)
        ttk.Label(input_frame, text="Unique Name:", style="CustomLabel.TLabel").grid(row=row, column=0, sticky="w", pady=2)

        # Create frame to hold the combobox and keep layout clean
        combo_frame = ttk.Frame(input_frame)
        combo_frame.grid(row=row, column=1, sticky="w", pady=2)

        # History Dropdown - editable
        self.combo_history = ttk.Combobox(
            combo_frame,
            textvariable=self.armammo_name_var,
            state="normal",
            width=25,
            style="White.TCombobox"
        )
        self.combo_history.grid(row=0, column=0)

        # Bind selection event to load data
        self.combo_history.bind("<<ComboboxSelected>>", lambda e: self._on_history_select())

        # Store reference to entry-style access if needed
        self.entries["armammo_name"] = self.combo_history
        self.combo_history.bind('<BackSpace>', self._on_entry_backspace)
        self.combo_history.bind('<Delete>', self._on_entry_delete)

        # Track history ID mapping (Name -> DB Record ID)
        self.history_id_map = {}

        row += 1

        # 2. Cartridge Dropdown
        ttk.Label(input_frame, text="Cartridge:", style="CustomLabel.TLabel").grid(row=row, column=0, sticky="w", pady=2)
        self.combo_cartridge = ttk.Combobox(
            input_frame, textvariable=self.cartridge_var,
            values=list(CARTRIDGE_DEFAULTS.keys()), state="readonly", width=25
        )
        self.combo_cartridge.grid(row=row, column=1, sticky="w", pady=2)
        if CARTRIDGE_DEFAULTS:
            self.combo_cartridge.current(0)
        row += 1

        # 3. Firearm Class Dropdown
        ttk.Label(input_frame, text="Firearm Class:", style="CustomLabel.TLabel").grid(row=row, column=0, sticky="w", pady=2)
        self.combo_class = ttk.Combobox(
            input_frame, textvariable=self.firearm_class_var,
            values=firearm_classes_display, state="readonly", width=25
        )
        self.combo_class.grid(row=row, column=1, sticky="w", pady=2)
        self.combo_class.bind("<<ComboboxSelected>>", lambda e: self.update_action_dropdown())
        row += 1

        # 4. Action Type Dropdown (Dynamic based on Class)
        ttk.Label(input_frame, text="Action Type:", style="CustomLabel.TLabel").grid(row=row, column=0, sticky="w", pady=2)
        self.combo_action = ttk.Combobox(
            input_frame, textvariable=self.action_type_var,
            state="readonly", width=25
        )
        self.combo_action.grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        # --- Divider ---
        ttk.Separator(input_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        # 5. Gun Weight
        self.create_input_row(input_frame, "Gun Weight:", "gun_weight", "8.0", "lbs", row)
        row += 1

        # 6. Bullet Weight
        self.create_input_row(input_frame, "Bullet Weight:", "bullet_weight", "150.0", "grains", row)
        row += 1

        # 7. Muzzle Velocity
        self.create_input_row(input_frame, "Muzzle Velocity:", "muzzle_vel", "2750", "fps", row)
        row += 1

        # 8. Powder Charge
        self.create_input_row(input_frame, "Powder Charge:", "powder_charge", "", "grains", row)
        row += 1

        # --- Divider ---
        ttk.Separator(input_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        # 9. Muzzle Device
        ttk.Label(input_frame, text="Muzzle Device:", style="CustomLabel.TLabel").grid(row=row, column=0, sticky="w", pady=2)
        self.combo_device = ttk.Combobox(
            input_frame, textvariable=self.muzzle_device_var,
            values=muzzle_devices_display, state="readonly", width=25
        )
        self.combo_device.grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        # --- Divider ---
        ttk.Separator(input_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        # 10. Fit Factors (LOP, Comb, Buttplate)
        ttk.Label(input_frame, text="Stock Fit", style="Section.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
        row += 1

        # LOP
        ttk.Label(input_frame, text="LOP:", style="Small.TLabel").grid(row=row, column=0, sticky="w", pady=1)
        combo_lop = ttk.Combobox(input_frame, textvariable=self.lop_fit_var, values=lop_display, state="readonly", width=25)
        combo_lop.grid(row=row, column=1, sticky="w", pady=1)
        row += 1

        # Comb
        ttk.Label(input_frame, text="Comb Height:", style="Small.TLabel").grid(row=row, column=0, sticky="w", pady=1)
        combo_comb = ttk.Combobox(input_frame, textvariable=self.comb_fit_var, values=comb_display, state="readonly", width=25)
        combo_comb.grid(row=row, column=1, sticky="w", pady=1)
        row += 1

        # Buttplate
        ttk.Label(input_frame, text="Recoil Pad:", style="Small.TLabel").grid(row=row, column=0, sticky="w", pady=1)
        combo_butt = ttk.Combobox(input_frame, textvariable=self.buttplate_fit_var, values=buttplate_display, state="readonly", width=25)
        combo_butt.grid(row=row, column=1, sticky="w", pady=1)
        row += 1

        # --- Buttons ---
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=row+1, column=0, columnspan=2, pady=20)

        self.btn_calc = ttk.Button(btn_frame, text="Calculate", bootstyle="primary", command=self.on_calculate)
        self.btn_calc.pack(side=LEFT, padx=5)

        self.btn_save = ttk.Button(btn_frame, text="Save Data Set", bootstyle="success", command=self.on_save)
        self.btn_save.pack(side=LEFT, padx=5)

        # --- RIGHT COLUMN: COMPARISON GRID
        output_frame = ttk.LabelFrame(main_container, text="Results")
        output_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Configure Grid:
        # Col 0: Labels
        # Col 1-3: Data Sets
        output_frame.columnconfigure(0, weight=0)
        for i in range(1, 4):
            output_frame.columnconfigure(i, weight=1)

        current_row = 0

        # --- HEADERS ---

        lbl_blank = ttk.Label(output_frame, text="", font=(FONT_FAMILY, 10))
        lbl_blank.grid(row=current_row, column=0, sticky="w", pady=(10, 5), padx=5)

        # Data Set Headers
        headers = ["Data Set 1", "Data Set 2", "Data Set 3"]
        for i, txt in enumerate(headers, start=1):
            lbl = ttk.Label(output_frame, text=txt, style="Header.TLabel")
            lbl.grid(row=current_row, column=i, sticky="w", pady=(10, 5), padx=5)

        current_row += 1

        # --- DATA ROWS HELPER ---
        def add_comparison_row(label_text):
            nonlocal current_row

            # Label (Col 0)
            lbl_key = ttk.Label(output_frame, text=f"{label_text}:", style="Small.TLabel")
            lbl_key.grid(row=current_row, column=0, sticky="w", pady=2, padx=5)

            # Value Slots (Cols 1, 2, 3) - Stores references to 3 labels
            val_slots = []
            for col in range(1, 4):
                val_lbl = ttk.Label(output_frame, text="--", style="Small.TLabel")
                val_lbl.grid(row=current_row, column=col, sticky="w", pady=2, padx=5)
                val_slots.append(val_lbl)

            current_row += 1
            return val_slots

        # Create Input Rows
        self.rows_data = {}
        self.rows_data["name"] = add_comparison_row("Unique Name")
        self.rows_data["cartridge"] = add_comparison_row("Cartridge Selected")
        self.rows_data["class"] = add_comparison_row("Firearm Class")
        self.rows_data["action"] = add_comparison_row("Action Type")

        self.rows_data["gun_wt"] = add_comparison_row("Gun Weight")
        self.rows_data["bull_wt"] = add_comparison_row("Bullet Weight")
        self.rows_data["vel"] = add_comparison_row("Muzzle Velocity")
        self.rows_data["powder"] = add_comparison_row("Powder Charge")
        self.rows_data["device"] = add_comparison_row("Muzzle Device")

        self.rows_data["lop"] = add_comparison_row("LOP")
        self.rows_data["comb"] = add_comparison_row("Comb Height")
        self.rows_data["butt"] = add_comparison_row("Recoil Pad")

        # --- DIVIDER BEFORE RESULTS (Stretches across all 4 cols) ---
        ttk.Separator(output_frame, orient="horizontal").grid(row=current_row, column=0, columnspan=4, sticky="ew", pady=10)
        current_row += 1

        # Calculated Results Header
        lbl_res_header = ttk.Label(output_frame, text="Calculated Results", style="Section.TLabel")
        lbl_res_header.grid(row=current_row, column=0, columnspan=4, sticky="w", pady=(5, 5))
        current_row += 1

        # Result Rows (Bold Values)
        result_configs = [
            ("Free Recoil Energy", "recoil_energy_output", "ft-lbs"),
            ("Recoil Velocity", "recoil_velocity_output", "fps"),
            ("Avg Impulse Force", "avg_impulse_output", "lbf"),
            ("Perceived Recoil Score", "perceived_score", "/10")
        ]

        self.rows_results = {}

        for label_text, var_key, unit in result_configs:
            # Key
            lbl_title = ttk.Label(output_frame, text=label_text, style="Small.TLabel")
            lbl_title.grid(row=current_row, column=0, sticky="w", pady=2, padx=5)

            # Value Slots (Cols 1, 2, 3)
            res_slots = []
            for col in range(1, 4):
                val_frame = ttk.Frame(output_frame)
                val_frame.grid(row=current_row, column=col, sticky="w", pady=2, padx=5)

                # Bold Value
                val_lbl = ttk.Label(val_frame, text="--", style="Bold.TLabel")
                val_lbl.pack(side="left")

                # Unit (Plain text)
                unit_lbl = ttk.Label(val_frame, text=unit, style="Unit.TLabel")
                unit_lbl.pack(side="left", padx=(2, 0))

                res_slots.append(val_lbl)

            self.rows_results[var_key] = res_slots
            current_row += 1

        # --- Place Icon in Bottom Left of Results Section ---
        if hasattr(self, "results_icon") and self.results_icon:
            lbl_icon = ttk.Label(output_frame, image=self.results_icon)
            # Place in next row, column 0, aligned West (left) with padding
            lbl_icon.grid(row=current_row, column=0, sticky="w", pady=(10, 5), padx=(30, 0))

        # --- Hamburger menu toggle for Results
        def toggle_menu(event=None):

            if not hasattr(self, "_app_menu"):
                self._app_menu = tk.Menu(self.root, tearoff=0,
                                        font=(FONT_FAMILY, 10),
                                        borderwidth=0,
                                        relief="flat")

                def close_and_show(title, msg):
                    try:
                        if hasattr(self, "_app_menu"):
                            try:
                                self._app_menu.unpost()
                            except Exception:
                                pass
                    finally:
                        show_themable_dialog(self.root, title, msg, kind="info")

                help_text = (
                    "1. enter a unique name if you want to save a dataset for later use; otherwise, can skip\n\n"
                    "2. select cartridge, firearm class, and action type from the drop-down menus\n\n"
                    "3. enter gun weight, bullet weight, and muzzle velocity\n\n"
                    "4. enter a powder charge if known (calculator will estimate if left blank)\n\n"
                    "5. select muzzle device, LOP, comb height, and recoil pad from drop-down menus\n\n"
                    "6. press blue Calculate button to kick off the calculator; data will show up in the left Results section in the order entered\n\n"
                    "7. press green Save Data Set button if you want to use the information later without having to re-enter"
                )

                about_text = (
                    "1. What is this?\n"
                    "The Bcalc Recoil Calculator is an open-source firearm recoil calculator.\n"
                    "You can enter specific firearm and ammo data and the calculator will estimate:\n"
                    " - free recoil energy:  total energy absorbed\n"
                    " - recoil velocity:  speed the firearm moves backwards\n"
                    " - average impulse force:  average force on hands/ shoulder\n"
                    " - perceived recoil score:  estimate for recoil comparisons\n\n"
                    "An internet connection is not required once installed.\n"
                    "No user data is transmitted.\n\n"
                    "2. Who is this for?\n"
                    "Anyone interested in comparing recoil related calculations of different firearm and ammunition combinations.\n\n"
                    "3. Why?\n"
                    "To create an application that provides interesting firearm associated data. This calculator is provided for entertainment and educational purposes."
                )

                self._app_menu.add_command(label="About", command=lambda: close_and_show("About", about_text))
                self._app_menu.add_command(label="User Guide", command=lambda: close_and_show("User Guide", help_text))
                self._app_menu.add_command(label="Credits", command=lambda: close_and_show("Credits", "Bcalc Recoil Calculator\n\nCreated by Brian Calc."))
                self._app_menu.add_command(label="License", command=lambda: close_and_show("License", "GNU General Public License (GPL) Version 3."))
                self._app_menu.add_separator()
                self._app_menu.add_command(label="Exit", command=self.root.quit)

            # Toggle posted state
            if getattr(self, "menu_btn", None) and getattr(self.menu_btn, "_menu_open", False):
                try:
                    self._app_menu.unpost()
                except Exception:
                    pass
                self.menu_btn._menu_open = False
            else:

                if getattr(self, "menu_btn", None):
                    self.menu_btn.update_idletasks()
                    estimated_height = 180
                    x_pos = self.menu_btn.winfo_rootx() - 30
                    y_pos = self.menu_btn.winfo_rooty() - estimated_height
                    if y_pos < 0:
                        y_pos = 0
                    try:
                        self._app_menu.post(x_pos, y_pos)
                        self.menu_btn._menu_open = True
                    except Exception:
                        pass

        # Place hamburger button in bottom-right of Results section
        self.menu_btn = ttk.Button(
            output_frame,
            text="\u2261",
            width=3,
            command=toggle_menu,
            style="TButton"
        )

        self.menu_btn.grid(row=current_row, column=3, sticky="e", padx=(0, 10), pady=(35, 5))

    def create_input_row(self, parent, label_text, var_key, default, unit, row):
        ttk.Label(parent, text=label_text, style="CustomLabel.TLabel").grid(row=row, column=0, sticky="w", pady=2)

        entry_frame = ttk.Frame(parent)
        entry_frame.grid(row=row, column=1, sticky="w", pady=2)

        entry = ttk.Entry(entry_frame, width=27, justify='center', style="White.TEntry")
        entry.insert(0, default)
        entry.grid(row=0, column=0, sticky="w") # Anchor left

        unit_lbl = ttk.Label(entry_frame, text=unit, style="Unit.TLabel")
        unit_lbl.grid(row=0, column=1, padx=(5, 0))

        self.entries[var_key] = entry
        entry.bind('<BackSpace>', self._on_entry_backspace)
        entry.bind('<Delete>', self._on_entry_delete)

        return entry

    def _refresh_history_dropdown(self):

        try:
            records = get_history(limit=50)
            if not records:
                self.combo_history['values'] = []
                self.history_id_map = {}
                return

            display_list = []
            self.history_id_map = {}

            for r in records:

                name = r.get('armammo_name', 'Unnamed') or 'Unnamed'
                ts = r.get('timestamp', '')
                display_date = str(ts)[:10] if ts else ""
                text = f"{name} ({display_date})" if display_date else name

                display_list.append(text)
                self.history_id_map[text] = r['id']

            self.combo_history['values'] = display_list

        except Exception as e:
            print(f"Error loading history: {e}")
            self.combo_history['values'] = []

    def _on_history_select(self):
        """Load full calculation data when a history item is selected."""
        selected_text = self.combo_history.get()

        if not selected_text or selected_text not in self.history_id_map:
            return

        record_id = self.history_id_map[selected_text]

        import sqlite3
        from db_manager import get_db_path

        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()

            # SQL Query Order
            query = """
                SELECT
                    armammo_name,       -- Index 0
                    firearm_class,      -- Index 1
                    action_type,        -- Index 2
                    gun_weight,         -- Index 3
                    bullet_weight,      -- Index 4
                    muzzle_vel,         -- Index 5
                    powder_charge,      -- Index 6
                    muzzle_device,      -- Index 7
                    lop_fit,            -- Index 8
                    comb_fit,           -- Index 9
                    buttplate_fit       -- Index 10
                FROM calculations
                WHERE id = ?
            """
            cursor.execute(query, (record_id,))
            row = cursor.fetchone()
            conn.close()

            if row:


                # 1. Name
                if row[0]:
                    self.armammo_name_var.set(row[0])

                # 2. Firearm Class + Refresh Action Dropdown
                if row[1]:
                    self.firearm_class_var.set(row[1])
                    self.update_action_dropdown()

                # 3. Action Type (Map Internal Key → Display Name)
                if row[2]:
                    action_key = row[2]
                    current_map = getattr(self, 'action_combo_mapping', {})
                    # Find display name matching this key
                    found_disp = next((k for k, v in current_map.items() if v == action_key), None)
                    self.action_type_var.set(found_disp or action_key)

                # 4. Muzzle Device
                if row[7]:
                    self.muzzle_device_var.set(row[7])

                # 5. Fits
                fit_to_label = {
                    # LOP Mappings
                    "too_short": "too short",
                    "just_right": "just right",
                    "too_long": "too long",

                    # Comb Mappings
                    "low": "low cheek weld",
                    "just_right": "perfect cheek weld",
                    "high": "high cheek weld",

                    # Buttplate Mappings
                    "hard": "hard rubber/plastic",
                    "soft": "soft recoil pad"
                }

                # Helper to safely get label or fallback to key
                def get_fit_label(key):
                    if not key: return "just right" # Default
                    return fit_to_label.get(key.lower(), key.replace("_", " "))

                # Apply to fields
                self.lop_fit_var.set(get_fit_label(row[8]))
                self.comb_fit_var.set(get_fit_label(row[9]))
                self.buttplate_fit_var.set(get_fit_label(row[10]))

                # 6. Numeric Fields (Gun Weight, Bullet Weight, Velocity)
                for key, idx in [("gun_weight", 3), ("bullet_weight", 4), ("muzzle_vel", 5)]:
                    val = row[idx]
                    if val is not None:
                        self.entries[key].delete(0, tk.END)
                        self.entries[key].insert(0, str(val))
                    else:
                        self.entries[key].delete(0, tk.END)


                # Powder Charge
                p_val = row[6]
                if p_val is not None:
                    self.entries["powder_charge"].delete(0, tk.END)
                    self.entries["powder_charge"].insert(0, str(p_val))
                else:
                    self.entries["powder_charge"].delete(0, tk.END)

        except Exception as e:
            print(f"Error loading record: {e}")

    def setup_cartridge_logic(self):
        """Bind cartridge selection to auto-fill data."""
        def on_cartridge_select(event=None):
            selected = self.cartridge_var.get()
            if not selected or selected not in CARTRIDGE_DEFAULTS:
                return

            data = CARTRIDGE_DEFAULTS[selected]

            # Update inputs
            for key in ["bullet_weight", "muzzle_vel", "powder_charge"]:
                if key in self.entries and key in data:
                    self.entries[key].delete(0, tk.END)
                    self.entries[key].insert(0, str(data[key]))




        self.combo_cartridge.bind("<<ComboboxSelected>>", on_cartridge_select)

    def update_action_dropdown(self):
        """Update the Action Type dropdown based on selected Firearm Class."""
        display_class = self.firearm_class_var.get()

        # Map display name to internal key
        internal_key = CLASS_KEY_MAP.get(display_class, display_class)

        # Get the map {display: key} for this class
        action_map = FIREARM_CLASSES.get(internal_key, {}).get("valid_actions_map", {})


        if not action_map:
            valid_keys = FIREARM_CLASSES.get(internal_key, {}).get("valid_actions", [])
            action_map = {k: k for k in valid_keys}

        # The keys of the map are the display names
        valid_display_names = list(action_map.keys())

        # Store the mapping for gather_inputs (Label -> Key)
        self.action_combo_mapping = action_map

        # Set the Combobox values
        self.combo_action['values'] = valid_display_names

        # Handle current selection
        current_val = self.action_type_var.get()
        found = False

        # Check if current_val matches any display name
        if current_val in valid_display_names:
            found = True
        else:
            # Check if current_val matches a key (case insensitive fallback)
            for val in valid_display_names:
                if val.lower() == current_val.lower():
                    self.action_type_var.set(val)
                    found = True
                    break

        # Default to first if nothing found
        if not found:
            self.action_type_var.set(valid_display_names[0] if valid_display_names else "")

    def gather_inputs(self) -> Dict[str, Any]:
        """Collect all input values from the GUI into a dictionary."""
        try:
            name_val = self.entries["armammo_name"].get().strip()
            gun_w = float(self.entries["gun_weight"].get())
            bull_w = float(self.entries["bullet_weight"].get())
            vel = int(float(self.entries["muzzle_vel"].get()))
            pow_str = self.entries["powder_charge"].get().strip()
            if not pow_str or pow_str.lower() == "none":
                powder = None
            else:
                powder = float(pow_str)
        except ValueError:
            raise ValueError("Please ensure all numeric fields contain valid numbers.")


        # Helper to map Fit Display Label -> Internal Key
        def get_fit_key(var_obj):
            val = var_obj.get()

            # Direct mapping: Display Label -> Internal Calculation Key
            # LOP
            if val == "just right": return "right"
            if val == "too long": return "long"
            if val == "too short": return "short"

            # Comb
            if val == "low cheek weld": return "low"
            if val == "perfect cheek weld": return "right"
            if val == "high cheek weld": return "high"

            # Buttplate
            if val == "hard rubber/plastic": return "hard"
            if val == "soft recoil pad": return "soft"


            return "right"

        # Map Action Display Name -> Internal Key using stored mapping
        action_label = self.action_type_var.get()
        # Direct lookup in our map (which is now {label: key})
        action_key = getattr(self, 'action_combo_mapping', {}).get(action_label, action_label)

        return {
            "armammo_name": name_val,
            "firearm_class": self.firearm_class_var.get(),
            "action_type": action_key,
            "gun_weight": gun_w,
            "bullet_weight": bull_w,
            "muzzle_vel": vel,
            "powder_charge": powder,
            "muzzle_device": self.muzzle_device_var.get(),
            "lop_fit": get_fit_key(self.lop_fit_var),
            "comb_fit": get_fit_key(self.comb_fit_var),
            "buttplate_fit": get_fit_key(self.buttplate_fit_var)
        }

    def _on_entry_backspace(self, event):
        widget = event.widget
        current_text = widget.get()
        cursor_pos = widget.index(tk.INSERT)
        if cursor_pos > 0:
            new_text = current_text[:cursor_pos-1] + current_text[cursor_pos:]
            widget.delete(0, tk.END)
            widget.insert(0, new_text)
            widget.icursor(cursor_pos - 1)
        return 'break'

    def _on_entry_delete(self, event):
        widget = event.widget
        current_text = widget.get()
        cursor_pos = widget.index(tk.INSERT)
        if cursor_pos < len(current_text):
            new_text = current_text[:cursor_pos] + current_text[cursor_pos+1:]
            widget.delete(0, tk.END)
            widget.insert(0, new_text)
            widget.icursor(cursor_pos)
        return 'break'

    def on_calculate(self):
        """Perform calculation and update UI. Rotates through Data Sets 1-3."""
        try:
            inputs = self.gather_inputs()
            result = calculate_recoil(**inputs)
            self.calculated_result = result

            # Determine which column to update (0, 1, or 2)
            # Cycle: 0 -> 1 -> 2 -> 0 -> 1...
            target_idx = self.calc_counter % 3

            # --- UPDATE THE TARGET COLUMN ---

            # Inputs
            self.rows_data["name"][target_idx].config(text=inputs.get("armammo_name", "") or "--")
            self.rows_data["cartridge"][target_idx].config(text=self.cartridge_var.get() or "--")
            self.rows_data["class"][target_idx].config(text=inputs.get("firearm_class", "--"))
            self.rows_data["action"][target_idx].config(text=inputs.get("action_type", "--"))

            self.rows_data["gun_wt"][target_idx].config(text=f"{inputs['gun_weight']} lbs")
            self.rows_data["bull_wt"][target_idx].config(text=f"{inputs['bullet_weight']} gr")
            self.rows_data["vel"][target_idx].config(text=f"{int(inputs['muzzle_vel'])} fps")

            actual_powder = result["parameters_used"]["powder_charge_used"]
            self.rows_data["powder"][target_idx].config(text=f"{round(actual_powder, 1)} gr")

            self.rows_data["device"][target_idx].config(text=inputs.get("muzzle_device", "--"))
            self.rows_data["lop"][target_idx].config(text=self.lop_fit_var.get() or "--")
            self.rows_data["comb"][target_idx].config(text=self.comb_fit_var.get() or "--")
            self.rows_data["butt"][target_idx].config(text=self.buttplate_fit_var.get() or "--")

            # Results
            self.rows_results["recoil_energy_output"][target_idx].config(text=str(result["recoil_energy_output"]))
            self.rows_results["recoil_velocity_output"][target_idx].config(text=str(result["recoil_velocity_output"]))
            self.rows_results["avg_impulse_output"][target_idx].config(text=str(round(result["avg_impulse_output"])))
            self.rows_results["perceived_score"][target_idx].config(text=str(result["perceived_score"]))

            # Increment counter for next click
            self.calc_counter += 1

        except ValueError as e:
            messagebox.showerror("Calculation Error", str(e))
            self.calculated_result = None

    def on_save(self):
        """Save current calculation to database."""
        if not self.calculated_result:
            show_themable_dialog(self.root, "No Data", "Please Calculate first before saving.", kind="warning")
            return

        try:
            inputs = self.gather_inputs()
            record_id = save_calculation(inputs, self.calculated_result, user_notes="Manual Save")
            show_themable_dialog(self.root, "Saved", f"Saved successfully (ID: {record_id}).", kind="info")
        except Exception as e:
            show_themable_dialog(self.root, "Save Failed", str(e), kind="error")

#decided to remove - leaving in as may want to return to later
    #def on_view_history(self):
        #self.history_data = get_history(limit=10)
        #if not self.history_data:
            #messagebox.showinfo("History", "No previous calculations found.")
        #else:
            #msg = f"Found {len(self.history_data)} recent records:\n\n"
            #for r in self.history_data[:5]:  # Show top 5
               #msg += f"{r['timestamp']} | {r['firearm_class']} ({r['action_type']})\n"
                #msg += f"  - Score: {r['perceived_score']} | E: {r['recoil_energy_output']} ft-lbs\n\n"
                #msg += "... (use Comparison View for full details)"
            #messagebox.showinfo("Recent History", msg)

    def cleanup(self):
        """Clean up resources before window is destroyed."""
        pass



def main():
    root = ttk.Tk()
    app = RecoilCalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
