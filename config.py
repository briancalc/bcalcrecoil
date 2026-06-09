# config.py

import csv
from pathlib import Path

# --- PATHS ---
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
DATA_DIR = Path(__file__).resolve().parent / "datadb"

# --- HELPER TO LOAD LISTS FROM CSV (with header row) ---
def load_csv_list(filename):
    filepath = RESOURCES_DIR / filename
    if not filepath.exists():
        print(f"Warning: {filepath} not found.")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        # Skip header row
        try:
            next(reader)
        except StopIteration:
            return []

        # Read remaining rows (first column only)
        return [row[0].strip() for row in reader if row and row[0].strip()]

# --- HELPER TO LOAD ACTION MAPS (Display Name -> Key) ---
def load_action_map(filename):
    filepath = RESOURCES_DIR / filename
    if not filepath.exists():
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            next(reader) # Skip header
        except StopIteration:
            return {}

        # Values are already normalized keys (e.g., "bolt action")
        actions = [row[0].strip() for row in reader if row and row[0].strip()]
        # Map: Display Name -> Internal Key (same string in this case)
        return {a: a for a in actions}


# --- APPLICATION CONFIGURATION ---
APP_NAME = "BC Calc Recoil"
VERSION = "1.0"


# --- FIREARM CLASS CONFIGURATION (Static Physics) ---
FIREARM_CLASSES = {
    "handgun": {
        "base_impulse": 0.0012,
        "gas_multiplier": 1.50,
        "valid_actions": [],
        "valid_actions_map": {}
    },
    "carbine": {
        "base_impulse": 0.0015,
        "gas_multiplier": 1.60,
        "valid_actions": [],
        "valid_actions_map": {}
    },
    "rifle_standard": {
        "base_impulse": 0.0020,
        "gas_multiplier": 1.75,
        "valid_actions": [],
        "valid_actions_map": {}
    },
    "rifle_long": {
        "base_impulse": 0.0025,
        "gas_multiplier": 1.80,
        "valid_actions": [],
        "valid_actions_map": {}
    },
    "shotgun_standard": {
        "base_impulse": 0.0018,
        "gas_multiplier": 1.50,
        "valid_actions": [],
        "valid_actions_map": {}
    },
    "shotgun_long": {
        "base_impulse": 0.0022,
        "gas_multiplier": 1.25,
        "valid_actions": [],
        "valid_actions_map": {}
    }
}

# --- ACTION TYPE MODIFIERS
ACTION_MODIFIERS = {
    "bolt_action": {"impulse_mult": 0.95},
    "lever_action": {"impulse_mult": 1.05},
    "semi_auto": {"impulse_mult": 1.15},
    "pump_action": {"impulse_mult": 1.08},
    "break_action": {"impulse_mult": 0.98},
    "revolver": {"impulse_mult": 1.02},
    # Add other keys if your CSVs include them
}

# --- MUZZLE DEVICE REDUCTIONS
MUZZLE_DEVICES = {
    "none": {"label": "None", "multiplier": 1.0},
    "flash_hider": {"label": "Flash Hider", "multiplier": 0.98},
    "moderate_brake": {"label": "Moderate Brake", "multiplier": 0.70},
    "aggressive_brake": {"label": "Aggressive Brake", "multiplier": 0.55},
    "suppressor": {"label": "Suppressor", "multiplier": 0.82}
}


# --- HELPERS FOR NORMALIZATION ---
def normalize_key(val):

    if not val:
        return ""
    return val.lower().replace(" ", "_").replace(".", "").replace(":", "")


def map_muzzle_device(display_name):
    """Map CSV muzzle device name to internal key."""
    norm = normalize_key(display_name)

    # Try direct match first
    if norm in MUZZLE_DEVICES:
        return norm

    # Try pattern matching
    if "flash" in norm:
        return "flash_hider"
    elif "brake" in norm and "agg" in norm:
        return "aggressive_brake"
    elif "brake" in norm and "mod" in norm:
        return "moderate_brake"
    elif "supp" in norm:
        return "suppressor"
    elif "none" in norm:
        return "none"

    # Default fallback
    return "none"


# --- LOAD DATA FROM CSV FILES ---

# 1. Load Firearm Classes (for UI dropdown)
firearm_classes_display = load_csv_list("firearmclass.csv")

# Map display names to keys by normalizing
CLASS_KEY_MAP = {}
for display in firearm_classes_display:
    CLASS_KEY_MAP[display] = normalize_key(display)

# 2. Load Actions SPECIFIC to each class (Direct Mapping)
# Handguns
action_map_handgun = load_action_map("actionhandgun.csv")

# Carbines: Fallback to Rifle Standard if no specific file exists
if Path(RESOURCES_DIR / "actioncarbine.csv").exists():
    action_map_carbine = load_action_map("actioncarbine.csv")
else:
    # Fallback to Rifle Standard actions for Carbine
    action_map_carbine = load_action_map("actionriflestandard.csv")

# Rifles (Standard & Long)
action_map_rifle_std = load_action_map("actionriflestandard.csv")
action_map_rifle_long = load_action_map("actionriflelong.csv")

# Shotguns (Standard & Long)
action_map_shotgun_std = load_action_map("actionshotgunstandard.csv")
action_map_shotgun_long = load_action_map("actionshotgunlong.csv")

# Assign Maps to FIREARM_CLASSES
FIREARM_CLASSES["handgun"]["valid_actions_map"] = action_map_handgun
FIREARM_CLASSES["carbine"]["valid_actions_map"] = action_map_carbine
FIREARM_CLASSES["rifle_standard"]["valid_actions_map"] = action_map_rifle_std
FIREARM_CLASSES["rifle_long"]["valid_actions_map"] = action_map_rifle_long
FIREARM_CLASSES["shotgun_standard"]["valid_actions_map"] = action_map_shotgun_std
FIREARM_CLASSES["shotgun_long"]["valid_actions_map"] = action_map_shotgun_long

FIREARM_CLASSES["handgun"]["valid_actions"] = list(action_map_handgun.keys())
FIREARM_CLASSES["carbine"]["valid_actions"] = list(action_map_carbine.keys())
FIREARM_CLASSES["rifle_standard"]["valid_actions"] = list(action_map_rifle_std.keys())
FIREARM_CLASSES["rifle_long"]["valid_actions"] = list(action_map_rifle_long.keys())
FIREARM_CLASSES["shotgun_standard"]["valid_actions"] = list(action_map_shotgun_std.keys())
FIREARM_CLASSES["shotgun_long"]["valid_actions"] = list(action_map_shotgun_long.keys())

# 3. Load Muzzle Devices (display names for UI)
muzzle_devices_display = load_csv_list("muzzledevice.csv")

# Create lookup: display_name -> internal_data
MUZZLE_DISPLAY_TO_INTERNAL = {}
for display in muzzle_devices_display:
    internal_key = map_muzzle_device(display)
    if internal_key in MUZZLE_DEVICES:
        MUZZLE_DISPLAY_TO_INTERNAL[display] = MUZZLE_DEVICES[internal_key]
    else:
        MUZZLE_DISPLAY_TO_INTERNAL[display] = {"label": display, "multiplier": 1.0}

# 4. Load Fit Penalties
FIT_PENALTIES = {}
fit_penalties_path = RESOURCES_DIR / "fitpenalties.csv"

if fit_penalties_path.exists():
    with open(fit_penalties_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row.get('Category', '').strip().lower()
            condition = row.get('Condition', '').strip().lower()
            label = row.get('Label', '').strip()
            try:
                points = float(row.get('Points', 0))
            except ValueError:
                points = 0.0

            if category not in FIT_PENALTIES:
                FIT_PENALTIES[category] = {}

            FIT_PENALTIES[category][condition] = {
                "label": label,
                "points": points
            }

#5 BUILD DISPLAY LISTS FOR FIT FACTORS
# Extract the 'label' from each category to use as dropdown values
lop_display = [FIT_PENALTIES["lop"][k]["label"] for k in FIT_PENALTIES.get("lop", {})]
comb_display = [FIT_PENALTIES["comb"][k]["label"] for k in FIT_PENALTIES.get("comb", {})]
buttplate_display = [FIT_PENALTIES["buttplate"][k]["label"] for k in FIT_PENALTIES.get("buttplate", {})]


# 6. Load Cartridge Defaults
CARTRIDGE_DEFAULTS = {}
cartridge_path = RESOURCES_DIR / "cartridge.csv"

if cartridge_path.exists():
    with open(cartridge_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = None

            for key in ['Caliber', 'Name', 'Cartridge']:
                if key in row and row[key]:
                    name = row[key].strip()
                    break

            if name:
                # Parse numeric fields safely
                try:
                    bw = float(row.get('Bullet_Weight', row.get('Bullet Weight', 0)))
                    mv = float(row.get('Muzzle_Vel', row.get('Muzzle Velocity', 0)))
                except ValueError:
                    bw = 0
                    mv = 0

                pc_str = row.get('Powder_Charge', row.get('Powder Charge', ''))
                pc = float(pc_str) if pc_str and str(pc_str).strip() else None

                CARTRIDGE_DEFAULTS[name] = {
                    "bullet_weight": bw,
                    "muzzle_vel": mv,
                    "powder_charge": pc
                }
