"""Shared constants and parameter sets for the stepper-drive feasibility simulation (ASCII only).

Every number is tagged [DS] datasheet / repo value, [CALC] derived, or [GUESS] assumption.
"""
import math
from dataclasses import dataclass, field
from typing import List

# ---- timing -------------------------------------------------------------
DT = 1.0 / 200.0          # [repo] control loop 200 Hz (cdtp_config.h)
SUB = 20                  # plant substeps per control tick -> 4 kHz physics
DTP = DT / SUB
TIMER_HZ = 20000.0        # [GUESS] step-pulse ISR timer rate (DDA), 20 kHz
MAX_STEPS_PER_SUB = int(TIMER_HZ * DTP)   # one step per timer tick at most (5 per substep)

# ---- stepper geometry ---------------------------------------------------
FULL_STEPS = 200          # [DS] 1.8 deg motor
MICRO = 16                # [task] 1/16 microstepping (DRV8825 MODE pins)
MSTEP = 2.0 * math.pi / (FULL_STEPS * MICRO)   # rad of rotor per microstep
NP = FULL_STEPS / 4       # electrical periods per rev (50): 4 full steps = 360 electrical deg
DRV8825_MAX_STEP_HZ = 250000.0   # [DS] DRV8825 STEP input limit (not the bottleneck, ISR is)

# ---- robot (sim/plant_nominal.h) ------------------------------------------
R_W = 0.0325              # [repo] wheel radius
M_WHEEL = 0.045           # [repo]
TRACK = 0.19              # [repo]
I_YAW = 0.012             # [repo]
L_COM = 0.0702            # [repo] COM height over axle (kept, per task)
I_BODY = 0.00737          # [repo]
G = 9.81
BOX_MASS, BOX_H = 0.06, 0.2065   # [repo] medicine box carried in the DC tests too
VBAT_NOM = 11.1           # [repo]

# ---- controller constants copied from cdtp_config.h ------------------------
COMP_ALPHA = 0.98
TRIM_RATE = 0.1
TRIM_MAX_DEG = 3.0
REF_SHAPING_W = 5.0
TH_FF_GAIN = 1.0
FALL_ANGLE_DEG = 40.0
FALL_HOLD_S = 0.05
ARM_ANGLE_DEG = 3.0
ARM_HOLD_S = 0.5
GLOVE_TIMEOUT_S = 0.30
STEP_DIST_M = 0.50
STEP_VMAX = 0.25
STEP_ACCEL = 0.40
TURN_ANGLE_DEG = 90.0
TURN_RATE_DEG = 90.0
TURN_ACCEL_DEG = 240.0


@dataclass
class MotorSpec:
    name: str
    m_body: float               # kg, everything except wheels (motors included)
    hold_ncm: float             # N.cm holding torque (datasheet)
    curve_rpm: List[float]
    curve_ncm: List[float]      # pull-out torque vs speed at 12 V (assumed, see RAPOR)
    J_rotor: float              # kg m^2
    mass_each: float            # kg
    note: str = ""


# Conservative pull-out curve for the 17HS4401 [GUESS]: no real datasheet curve was found
# (the task allows exactly this fallback): 40 N.cm @0, 25 @150 rpm, 15 @300 rpm, then flatter.
_RPM = [0.0, 150.0, 300.0, 600.0]
_NCM = [40.0, 25.0, 15.0, 8.0]

MOTORS = {
    "17HS4401": MotorSpec("17HS4401", 1.31, 40.0, _RPM, _NCM, 5.4e-6, 0.280,
                          "40 N.cm, 1.7 A, 1.5 ohm, 2.8 mH [DS]; rotor inertia 54 g.cm2 [typical]"),
    # 17HS3401S: curve scaled by 28/40 as instructed (assumption); rotor inertia guessed 3.5e-6
    "17HS3401S": MotorSpec("17HS3401S", 1.25, 28.0, _RPM, [v * 28.0 / 40.0 for v in _NCM], 3.5e-6, 0.220,
                           "28 N.cm min, 1.3 A, 220 g [listing]; curve = 17HS4401 curve x 0.7 [GUESS]"),
}


@dataclass
class PlantParams:
    motor: str = "17HS4401"
    m_body: float = 0.0          # filled from motor if 0
    l_com: float = L_COM
    I_body: float = I_BODY
    m_wheel: float = M_WHEEL
    r: float = R_W
    track: float = TRACK
    I_yaw: float = I_YAW
    box_mass: float = BOX_MASS
    box_h: float = BOX_H
    h_imu: float = 0.05
    imu_offset_deg: float = 0.0
    gyro_bias_dps: float = 0.0
    gyro_noise_dps: float = 0.05
    acc_noise: float = 0.03
    vib_acc: float = 0.30        # [GUESS] stepper vibration, m/s2 rms, constant while energised
    vbat: float = VBAT_NOM
    torque_scale: float = 1.0    # multiplies the pull-out curve (sensitivity cases)
    damp: float = 0.010          # [GUESS] N m s/rad electromagnetic damping vs field
    tau_c: float = 0.003         # [GUESS] N m bearing friction per motor (no gearbox)
    J_rotor: float = 0.0         # filled from motor if 0

    def __post_init__(self):
        spec = MOTORS[self.motor]
        if self.m_body == 0.0:
            self.m_body = spec.m_body
        if self.J_rotor == 0.0:
            self.J_rotor = spec.J_rotor
