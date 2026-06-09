# recoil_math.py

# gun_weight = lbs
# bullet_weight = grains
# muzzle_vel = f/s
# powder_charge = grains
# recoil velocity = f/s
# recoil energy = ft-lbs

from constants import (
    GRAINS_PER_POUND,
    GRAVITY_CONSTANT
)
from config import FIREARM_CLASSES, ACTION_MODIFIERS, MUZZLE_DEVICES, FIT_PENALTIES, normalize_key, map_muzzle_device, CLASS_KEY_MAP

def calculate_recoil(
    firearm_class: str,
    action_type: str,
    gun_weight: float,
    bullet_weight: float,
    muzzle_vel: float,
    powder_charge: float = None,
    muzzle_device: str = "none",
    lop_fit: str = "just_right",
    comb_fit: str = "just_right",
    buttplate_fit: str = "hard",
    armammo_name: str = ""
) -> dict:

    # --- 1. NORMALIZATION & MAPPING ---
    # Map Firearm Class Display Name -> Internal Key
    # e.g., "rifle: standard" -> "rifle_std"
    internal_firearm_class = CLASS_KEY_MAP.get(firearm_class, firearm_class)

    # Map Action Type Display Name -> Internal Key
    internal_action_type = action_type.lower().replace(" ", "_").replace(".", "")
    if "revolver" in internal_action_type:
        internal_action_type = "revolver"

    # Map Muzzle Device Display Name -> Internal Key
    # e.g., "brake: moderate" -> "moderate_brake"
    internal_muzzle_device = map_muzzle_device(muzzle_device)

    # --- 2. VALIDATION & CONFIG RETRIEVAL ---
    class_config = FIREARM_CLASSES.get(internal_firearm_class)
    if not class_config:
        raise ValueError(
            f"Invalid firearm_class: {firearm_class} (mapped to {internal_firearm_class}). "
            f"Valid types: {list(FIREARM_CLASSES.keys())}"
        )

    # Validate action type against the allowed actions for this class
    valid_actions = class_config.get("valid_actions", [])

    # Normalize the action_type again just in case it passed through multiple times
    check_action = internal_action_type.lower().replace("_", "_")

    if check_action not in valid_actions:
        found_match = False
        for va in valid_actions:
            va_normalized = va.lower().replace(" ", "_").replace(".", "")

            if va_normalized == check_action or va.replace("_", " ") == check_action.replace("_", " "):
                check_action = va_normalized
                found_match = True
                break

        if not found_match:
            raise ValueError(
                f"Action '{action_type}' is not valid for {firearm_class}. "
                f"Mapped to: {check_action}, Valid actions: {valid_actions}"
            )

    # Get Base Physics Constants
    base_impulse = class_config["base_impulse"]
    gas_multiplier = class_config["gas_multiplier"]

    # Apply Action Modifier to Impulse Time
    # Example: bolt_action (0.95) makes impulse shorter/sharper
    action_mod = ACTION_MODIFIERS.get(check_action, {}).get("impulse_mult", 1.0)
    impulse_time = base_impulse * action_mod

    # Muzzle Device Multiplier
    device_mult = MUZZLE_DEVICES.get(internal_muzzle_device, {}).get("multiplier", 1.0)

    # Handle Optional Powder Charge Input
    # Default estimation: 30% of bullet weight if not provided
    if powder_charge is None or powder_charge <= 0:
        powder_charge = bullet_weight * 0.30
        estimated_powder = True
    else:
        estimated_powder = False

    # --- 3. PHYSICS CALCULATIONS ---
    # Step A: Recoil velocity from projectile momentum
    recoil_vel_proj = (bullet_weight / GRAINS_PER_POUND * muzzle_vel) / gun_weight

    # Step B: Recoil velocity from powder gas expansion
    recoil_vel_gas = (powder_charge / GRAINS_PER_POUND * muzzle_vel * gas_multiplier) / gun_weight

    # Step C: Total Recoil Velocity
    recoil_velocity = recoil_vel_proj + recoil_vel_gas

    # Step D: Free Recoil Energy (ft-lbs)
    recoil_energy = (0.5 * gun_weight * recoil_velocity**2) / GRAVITY_CONSTANT

    # Step E: Average Impulse Force (lbf)
    momentum_lbf_s = (gun_weight * recoil_velocity) / GRAVITY_CONSTANT
    avg_impulse_force = momentum_lbf_s / impulse_time

    # --- 4. ADJUSTMENTS FOR MUZZLE DEVICES ---
    recoil_velocity_adj = recoil_velocity * device_mult
    recoil_energy_adj = recoil_energy * device_mult
    avg_impulse_force_adj = avg_impulse_force * device_mult

    # --- 5. PERCEIVED RECOIL SCORE (1-10) ---
    # A. Calculate Base Score from Energy
    base_score = 1.0
    if recoil_energy_adj <= 5:
        base_score = 1.0 + (recoil_energy_adj / 5.0) * 2
    elif recoil_energy_adj <= 15:
        base_score = 3.0 + ((recoil_energy_adj - 5) / 10.0) * 3
    elif recoil_energy_adj <= 30:
        base_score = 6.0 + ((recoil_energy_adj - 15) / 15.0) * 3
    else:
        base_score = 9.0 + ((recoil_energy_adj - 30) / 10.0)

    # B. Apply Impulse Time Modifier/ Snappiness
    impulse_modifier = 0.0
    if impulse_time < 0.0014:
        impulse_modifier = 1.5   # Very snappy (handguns, bolt)
    elif impulse_time < 0.0020:
        impulse_modifier = 0.5   # Moderate snap (carbines)
    elif impulse_time >= 0.0025:
        impulse_modifier = -0.5  # Smooth roll (long rifles, semi-autos)
    # Else: 0.0 (standard rifle)

    score_with_impulse = base_score + impulse_modifier

    # C. Apply Stock Fit Penalties
    fit_penalty = 0
    fit_penalty += FIT_PENALTIES["lop"].get(lop_fit, {}).get("points", 0)
    fit_penalty += FIT_PENALTIES["comb"].get(comb_fit, {}).get("points", 0)
    fit_penalty += FIT_PENALTIES["buttplate"].get(buttplate_fit, {}).get("points", 0)

    # D. Final Clamp (1.0 to 10.0)
    final_score = max(1.0, min(10.0, score_with_impulse + fit_penalty))

    # --- 6. RETURN RESULTS ---
    return {
        "recoil_energy_output": round(recoil_energy_adj, 2),
        "recoil_velocity_output": round(recoil_velocity_adj, 2),
        "avg_impulse_output": round(avg_impulse_force_adj, 2),
        "perceived_score": round(final_score, 1),
        "parameters_used": {
            #"armammo_name": armammo_name,
            "firearm_class_input": firearm_class,
            "firearm_class_mapped": internal_firearm_class,
            "action_type_input": action_type,
            "action_type_mapped": check_action,
            "muzzle_device_input": muzzle_device,
            "muzzle_device_mapped": internal_muzzle_device,
            "gas_multiplier": gas_multiplier,
            "base_impulse": base_impulse,
            "final_impulse_time": round(impulse_time, 5),
            "device_multiplier": device_mult,
            "powder_estimated": estimated_powder,
            "powder_charge_used": powder_charge
        }
    }
