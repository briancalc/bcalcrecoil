#db_manager.py

from pathlib import Path
import sqlite3
from typing import List, Dict, Any, Optional

DB_FILENAME = "recoil_data.db"


def get_db_path() -> str:
    project_root = Path(__file__).resolve().parent
    db_folder = project_root / "datadb"
    db_folder.mkdir(parents=True, exist_ok=True)
    return str(db_folder / DB_FILENAME)


def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()


    schema = """
    CREATE TABLE IF NOT EXISTS calculations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

        -- Inputs (Required)
        armammo_name TEXT,
        firearm_class TEXT NOT NULL,
        action_type TEXT NOT NULL,
        gun_weight REAL NOT NULL,
        bullet_weight REAL NOT NULL,
        muzzle_vel REAL NOT NULL,

        -- Powder Charge (nullable if never entered, but stores actual used value)
        powder_charge REAL,
        powder_estimated INTEGER DEFAULT 0,

        barrel_length_in REAL,

        -- Settings (Have defaults; prevent NULL surprises)
        muzzle_device TEXT NOT NULL DEFAULT 'none',
        lop_fit TEXT NOT NULL DEFAULT 'just_right',
        comb_fit TEXT NOT NULL DEFAULT 'just_right',
        buttplate_fit TEXT NOT NULL DEFAULT 'hard',

        notes TEXT,

        -- Outputs (Calculated results)
        recoil_energy_output REAL NOT NULL,
        recoil_velocity_output REAL NOT NULL,
        avg_impulse_output REAL NOT NULL,
        perceived_score REAL NOT NULL,

        -- Metadata (Snapshot of physics constants used)
        gas_multiplier REAL NOT NULL,
        final_impulse_time REAL NOT NULL,
        device_multiplier REAL NOT NULL
    );
    """

    # Create Index for fast retrieval of recent calculations
    index_schema = """
    CREATE INDEX IF NOT EXISTS idx_calculations_timestamp
    ON calculations(timestamp DESC);
    """

    try:
        cursor.executescript(schema)
        cursor.executescript(index_schema)
        conn.commit()
        print(f"[DB] Database and indexes initialized at {get_db_path()}")
    except sqlite3.Error as e:
        print(f"[DB] Error initializing database: {e}")
        raise e
    finally:
        conn.close()


def save_calculation(
    input_data: Dict[str, Any],
    calc_result: Dict[str, Any],
    user_notes: Optional[str] = None
) -> int:
    """
    Saves a calculation to the database using named parameters for safety and clarity.
    """

    # --- 1. VALIDATE REQUIRED INPUTS ---
    required_keys = [
        "firearm_class",
        "action_type",
        "gun_weight",
        "bullet_weight",
        "muzzle_vel"
    ]

    missing = []
    for key in required_keys:
        if key not in input_data or input_data[key] is None:
            missing.append(key)

    if missing:
        raise ValueError(f"Missing required input(s): {', '.join(missing)}")

    # Validate numeric fields have valid values
    numeric_checks = [
        ("gun_weight", 0.1),       # Must be > 0.1 lbs
        ("bullet_weight", 1),      # Must be > 1 grain
        ("muzzle_vel", 10),        # Must be > 10 fps
    ]

    for key, min_val in numeric_checks:
        val = input_data.get(key)
        if val is not None and val <= min_val:
            raise ValueError(f"Invalid {key}: must be greater than {min_val}")

    # Ensure calc_result has outputs
    if calc_result is None:
        raise ValueError("calc_result cannot be None")

    required_outputs = [
        "recoil_energy_output",
        "recoil_velocity_output",
        "avg_impulse_output",
        "perceived_score",
        "parameters_used"
    ]

    for key in required_outputs:
        if key not in calc_result:
            raise ValueError(f"calc_result missing output field: {key}")

    params = calc_result.get("parameters_used", {})
    if params.get("powder_charge_used") is None:
        raise ValueError("calc_result.parameters_used missing powder_charge_used")

    # --- 2. PREPARE DATA FOR INSERT ---
    row_data = {
        "armammo_name": input_data.get("armammo_name", ""),
        "firearm_class": input_data.get("firearm_class"),
        "action_type": input_data.get("action_type"),
        "gun_weight": input_data.get("gun_weight"),
        "bullet_weight": input_data.get("bullet_weight"),
        "muzzle_vel": input_data.get("muzzle_vel"),

        # Powder charge comes strictly from the math engine's final value
        "powder_charge": params.get("powder_charge_used"),
        "powder_estimated": 1 if params.get("powder_estimated") else 0,

        "barrel_length_in": input_data.get("barrel_length_in"),
        "muzzle_device": input_data.get("muzzle_device", "none"),
        "lop_fit": input_data.get("lop_fit", "just_right"),
        "comb_fit": input_data.get("comb_fit", "just_right"),
        "buttplate_fit": input_data.get("buttplate_fit", "hard"),
        "notes": user_notes,

        "recoil_energy_output": calc_result.get("recoil_energy_output"),
        "recoil_velocity_output": calc_result.get("recoil_velocity_output"),
        "avg_impulse_output": calc_result.get("avg_impulse_output"),
        "perceived_score": calc_result.get("perceived_score"),

        "gas_multiplier": params.get("gas_multiplier"),
        "final_impulse_time": params.get("final_impulse_time"),
        "device_multiplier": params.get("device_multiplier"),
    }

    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    sql = """
    INSERT INTO calculations (
        armammo_name, firearm_class, action_type, gun_weight, bullet_weight, muzzle_vel,
        powder_charge, powder_estimated, barrel_length_in,
        muzzle_device, lop_fit, comb_fit, buttplate_fit, notes,
        recoil_energy_output, recoil_velocity_output, avg_impulse_output, perceived_score,
        gas_multiplier, final_impulse_time, device_multiplier
    ) VALUES (
        :armammo_name, :firearm_class, :action_type, :gun_weight, :bullet_weight, :muzzle_vel,
        :powder_charge, :powder_estimated, :barrel_length_in,
        :muzzle_device, :lop_fit, :comb_fit, :buttplate_fit, :notes,
        :recoil_energy_output, :recoil_velocity_output, :avg_impulse_output, :perceived_score,
        :gas_multiplier, :final_impulse_time, :device_multiplier
    )
    """

    try:
        cursor.execute(sql, row_data)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"[DB] Error saving calculation: {e}")
        raise
    finally:
        conn.close()


def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves the most recent calculations.
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM calculations ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"[DB] Error retrieving history: {e}")
        return []
    finally:
        conn.close()


def delete_calculation(record_id: int) -> bool:
    """
    Deletes a specific calculation record.
    """
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM calculations WHERE id = ?", (record_id,))
        conn.commit()

        # rowcount > 0 means we matched and deleted at least one row
        return cursor.rowcount > 0
    except sqlite3.Error as e:

        print(f"[DB] Error deleting record {record_id}: {e}")
        raise  # Re-raise the exception
    finally:
        conn.close()
