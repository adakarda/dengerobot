# Stepper-drive feasibility study (open loop, DRV8825, 1/16 microstep)

Question: does the self-balancing robot still pass its acceptance tests (C1.1-C1.4, C2.1-C2.5, ON, GUV.1/2, robustness) when the two
encoder DC gearmotors are replaced by two NEMA17 steppers driven open loop (no encoder)? Two motors were evaluated side by side:
**17HS4401** (40 N.cm, 1.7 A, 280 g each, body mass 1.31 kg) and **17HS3401S** (28 N.cm, 1.3 A, 220 g each, body mass 1.25 kg).
Docking / IR approach (C3, C5) is out of scope and was not simulated.

Everything is in `sim_step/` (nothing else in the repository was touched). Python only, no firmware code was changed.
Rerun: `python sim_step/run_all.py` (about 4-5 min on a 12 core PC; `--quick` uses 5 instead of 20 randomised runs per case).

## 1. Verdict

**Yes, in simulation both steppers pass all acceptance tests with a large torque margin. Torque is not the limiting factor. What limits the
design is (a) the rotor/field resonance (damping is a guess), (b) vibration/noise-driven position wander that makes the strict
"hold within 3 cm for 3 s after 1 m" criterion marginal, and (c) the acceleration/speed caps I had to impose to keep the motors in sync in extreme kicks.**

* Nominal formal run (same seeds/thresholds as `sim/sim_main.cpp`): **all 12 tests PASS for both motors** (ON, C1.1, C1.2, C1.3, C1.4, GUV.2, C2.1-C2.5, GUV.1; C3/C5 not run).
* Torque margin (1 - |T|/pull-out, worst moment of each test, both motors): 17HS4401 min **0.71** (C1.3), 17HS3401S min **0.56** (C1.4 recovery).
  Peak torque demand per motor in the +-10 deg recovery is only **9.4 N.cm (4401)** and **11.5 N.cm (3401S)** against 35.5 and 26.2 N.cm available at that speed.
  In 20-run Monte Carlo sweeps (mass +-25 %, COM -25/+60 %, other uncertainties) the worst margin stays >= 0.51 and **no lost steps occurred in any of 320 randomised runs**.
* Recovery from +-10 deg takes 0.79-0.86 s (DC build: 1.44-1.48 s). Peak wheel speed 100-105 rpm (DC: 113 rpm).
* **Weak spot 1: 1 m + 3 s hold with the +-3 cm drift limit.** Formal run passes (26.5 / 20.1 mm, 4401; 26.3 / 7.3 mm, 3401S) but the limit is 30 mm and the DC build gets about 10 mm.
  In randomised runs the 3 cm criterion passes 13-20 of 20 depending on the case (nominal 18/20 and 20/20); the 5 cm criterion passes 18-20 of 20. This is IMU-noise/vibration-driven wander, not torque.
  The sensitivity table shows C1.2/C1.3 flipping to FAIL in several cases (vibration x3, torque x0.7, ...) for the same reason.
* **Weak spot 2: pull-out curve and damping are assumed, not measured** (see section 2). With the conservative curve all tests pass; the 17HS3401S still keeps margin >0.3 at half of the assumed torque; at 0.35 x torque it
  goes slightly into overload (margin -0.10, no pole slip). 17HS4401 keeps margin 0.36 at 0.35 x torque.
* **Which motor:** I would pick the **17HS3401S**: it passes everything with identical practical performance, is 120 g lighter, its 1.3 A rating fits a DRV8825 without a heat sink (a 17HS4401 at its full 1.7 A needs a heat sink and then the
  microstepped torque is only ~70 % of 40 N.cm anyway), and demand (6-12 N.cm) is under half of its derated pull-out. Choose the 17HS4401 only if a bench measurement of the real 3401S shows less than ~15 N.cm at 100 rpm / 11 V, or if the robot must survive pushes
  beyond about +-30 deg (with relaxed caps both recover 30 deg; at the next test angle, 35 deg, the 4401 sits at margin 0.01 and the 3401S slips 28 poles).
* **Biggest risk:** the model's electromagnetic damping of the rotor (guess 0.01 N.m.s/rad, about 3 % of critical). At 0.003 the 17HS4401 develops a 25-40 Hz limit cycle with 30 N.cm torque chatter during balance (still passed, but margin 0.20); in earlier
  controller iterations without the filtering described in section 4 it fell over. Bench-measure it, keep the software low-pass/notch on the acceleration command, and use mixed decay in the DRV8825.

## 2. Assumptions

### 2.1 Datasheet / repository based
| Item | Value | Source |
|---|---|---|
| Robot geometry | wheel r 32.5 mm, wheel mass 45 g, track 190 mm, I_body 0.00737, I_yaw 0.012, COM 70.2 mm, box 60 g at 206.5 mm | `sim/plant_nominal.h`, `sim/plant.h` |
| Body mass | 1.31 kg (17HS4401), 1.25 kg (17HS3401S), plus the 60 g medicine box as in the DC tests | task statement |
| Battery | 11.1 V nominal, 10.4-12.6 V in sweeps | repo |
| Loop, IMU, filter | 200 Hz, MPU6050 DLPF 42 Hz, accel noise 0.03 m/s2, gyro noise 0.05 dps, complementary filter 0.98/0.02 with the 1 g gating | `cdtp_config.h`, `imu_filter.h`, `plant.h` |
| Tilt/trim, reference shaping (5 rad/s), glove step 0.5 m @ 0.25 m/s, 0.4 m/s2, turn 90 deg @ 90 deg/s, 0.3 s timeout, fall 40 deg | ported | `robot_logic.cpp` |
| Stepper | 200 full steps, 1/16 microstep (3200 per rev, 0.064 mm of wheel per microstep), 50 electrical periods per rev | datasheet / task |
| 17HS4401 | 40 N.cm holding, 1.7 A, 1.5 ohm, 2.8 mH, 280 g | task statement |
| 17HS3401S | 28 N.cm min holding, 1.3 A, 220 g (R, L not given) | coordinator listing |
| DRV8825 | STEP input up to 250 kHz (not the bottleneck) | datasheet |

### 2.2 Guessed (clearly not measured)
| Item | Value used | Why / effect |
|---|---|---|
| **Pull-out torque curve 17HS4401** | 40 N.cm @ 0 rpm, 25 @ 150, 15 @ 300, 8 @ 600 (piecewise linear), for 12 V; speed axis stretched by 12/Vbat | A web search found no real curve (listings even disagree: 1.5 A vs 1.7 A, 1.8 ohm/4.2 mH vs 1.5 ohm/2.8 mH). Conservative fallback given in the task |
| **Pull-out torque 17HS3401S** | 17HS4401 curve x 28/40 | coordinator instruction |
| Torque sensitivity | x0.70, x0.50, x0.35 | x0.70 is also what a DRV8825 microstepping at 1.7 A *peak* really gives (vector torque = 0.707 x the full-step holding torque), so it is arguably the *expected* case, not a pessimistic one |
| Rotor inertia | 5.4e-6 kg m2 (4401), 3.5e-6 (3401S) | typical catalogue values |
| Electromagnetic damping | 0.010 N.m.s/rad per motor on (field speed - rotor speed); sensitivity 0.003 and 0.030 | decides the rotor/field resonance; no data |
| Bearing friction | 0.003 N.m Coulomb per motor, no gearbox | guess |
| Vibration into the accelerometer | 0.30 m/s2 rms constant while energised (DC build: 0.3 x (0.3+I/2)); sensitivity x3 | steppers vibrate even at rest |
| Step-pulse timer | 20 kHz DDA (phase accumulator), at most one step per tick | task suggests 20-40 kHz |
| IMU height | controller assumes 50 mm, plant 0-120 mm in sweeps | as in `plant.h` |
| Hand tilt in the +-10 deg tests | rotor assumed to follow the tilt (load angle kept); dead-reckoned position then starts about 6 mm off | physical hand tilt would slip poles by a few mm |

### 2.3 Not modelled (say so honestly)
Winding current dynamics and DRV8825 decay modes (lumped into the pull-out curve), DRV8825 thermal limit and Vref current error, step-rate resonance bands of the real motor, detent torque when unpowered
(ON test uses free-wheeling rotors), wheel-ground slip, supply sag/regenerative pumping of the 12 V rail, ESP32 ISR jitter. Docking / IR is not covered.

## 3. Model

* **Mechanics**: same wheel-pendulum equations as `sim/plant.h` (pitch, forward position, yaw), 4 kHz integration.
* **Stepper**: the controller commands a wheel acceleration, the velocity is integrated and ramped inside each 5 ms tick; a 20 kHz DDA turns it into microsteps (count is the controller's odometry).
  Per motor `T = T_pullout(field speed) * sin(50 * (field angle - rotor angle)) + c*(field speed - rotor speed) - friction`.
  Beyond 90 electrical degrees the sine falls again, the rotor runs away and slips whole electrical periods (**1 lost-step event = 4 full steps = 64 microsteps = 4.1 mm of wheel travel**); torque collapses naturally and can re-sync.
  Dead-reckoning cannot see a slip, so slips would show up as the "dead-reckoning error" column (none occurred).
* **Torque margin** = 1 - |T_el|/T_pullout(speed), minimum over the test window; negative means beyond 90 electrical degrees. "Per motor" torque is the maximum of the two motors; p99 is over 5 ms tick peaks.

## 4. Controller and gains

State `[x, v, theta, omega]`, input = common relative wheel acceleration `u` (rad/s2), LQR designed on the linear model (200 Hz ZOH, `tools/lqr_design.py` style, scipy `solve_discrete_are`).
`theta_dot_dot = (m g l theta - (a+bc) u)/D`, `v_dot = r (u + theta_dot_dot)`, with `a, bc, D` from the same inertia expressions as the DC model (gear ratio 1, rotor inertia in the wheel).

* Weights (Bryson, allowed error): x 0.06 m, v 0.10 m/s, theta 4 deg, omega 40 deg/s, u 100 rad/s2.
* Gains `u = -K (s - s_ref)` with `s = [ex (m), v - v_ref (m/s), theta - theta_ref - trim (rad), omega (rad/s)]`:
  * 17HS4401: `K = [-1455.9, -1424.2, -3021.5, -403.2]`
  * 17HS3401S: `K = [-1457.2, -1428.5, -3038.7, -409.3]`
  * lean feed-forward `theta_ref = 0.154 rad per m/s2 * a_ref` (same as DC); tilt trim, reference shaper (5 rad/s), trapezoid steps as in `robot_logic.cpp`.
* Measurements without an encoder: `x = r*(mean microsteps*2pi/3200) + r*theta_est`, `v = r*(commanded wheel speed + gyro rate)`, yaw angle/rate from the step difference (so turns are exact by construction, 90.0 deg).
* **Things I had to add to make it work** (found by simulation, documented in `controller.py`):
  1. **Accelerometer compensation:** the commanded wheel acceleration is known, so its contribution (plus the 50 mm IMU lever arm of the pitch acceleration) is removed from the accelerometer before the complementary filter.
     Without it the loop oscillated at about 0.8 Hz (+-4 cm, +-4 deg) because the acceleration command leaks into the angle estimate.
  2. **Low-pass on the acceleration command (10 Hz) and on the gyro used for feedback (20 Hz):** without them the rotor/field mode (about 25-40 Hz, lightly damped) is excited by the high loop gain and the motor chatters at pull-out torque.
  3. **Acceleration limits:** |u| <= 150 rad/s2 (4.9 m/s2 at the wheel), wheel speed <= 200 rpm, and a predicted-torque clamp so that |T_per motor| <= 0.8 x pull-out(speed) (in the +-10 deg recovery the 150 rad/s2 cap is active for the first few ticks; the torque clamp and the speed cap never became active).
* The weights were chosen from small sweeps on the same family of random seeds as the Monte Carlo, so robustness numbers are slightly optimistic. Thresholds were not changed.

## 5. Headline comparison with the DC build (`sim/results/summary.tsv`)

| Test (threshold) | DC build | 17HS4401 | 17HS3401S |
|---|---|---|---|
| ON unpowered falls < 5 s | 0.30 s | 0.22 s | 0.22 s |
| C1.1 30 s static (tilt < 5 deg, drift < 15 cm) | 0.70 deg, 1.6 cm | PASS 1.28 deg, 1.9 cm | PASS 1.29 deg, 2.9 cm |
| C1.2 1 m forward + hold (0.9-1.1 m, <3 cm) | 0.993 m, 10.1 mm, tilt 5.3 deg | PASS 1.018 m, 26.5 mm, 4.0 deg | PASS 1.021 m, 26.3 mm, 3.5 deg |
| C1.3 1 m back + hold | 1.005 m, 9.7 mm, 5.0 deg | PASS 0.995 m, 20.1 mm, 3.7 deg | PASS 0.993 m, 7.3 mm, 3.5 deg |
| C1.4 recovery +-10 deg (< 10 s) | 1.44 / 1.48 s, 14 / 13 cm | PASS 0.86 / 0.79 s, 13 / 12 cm | PASS 0.79 / 0.79 s, 12 / 13 cm |
| GUV.2 e-stop | PASS | PASS | PASS |
| C2.1 glove forward 0.5 m (+-0.1) | 0.75 s, 0.500 m | PASS 0.79 s, 0.533 m | PASS 0.79 s, 0.494 m |
| C2.2 glove back | 0.78 s, -0.492 m | PASS 0.77 s, -0.491 m | PASS 0.77 s, -0.491 m |
| C2.3 / C2.4 turn 90 deg (+-15) | 0.29 s, 90.0 deg | PASS 0.24 s, 90.0 deg | PASS 0.24 s, 90.0 deg |
| C2.5 hold after commands (< 3 cm, < 3 deg) | 12.4 mm, 0.43 deg | PASS 12.0 mm, 0.00 deg | PASS 0.6 mm, 0.00 deg |
| GUV.1 glove lost, step cut | 0.305 m | PASS 0.306 m | PASS 0.306 m |
| SAG static / recovery / 1 m <5 cm / <3 cm (DC: 40 random runs) | 40/40, 40/40 (<= 1.7 s), 40/40, 37/40 | "random" case (20 runs): 20/20, 20/20 (<= 0.98 s), 18/20, 14/20 | 20/20, 20/20 (<= 0.96 s), 19/20, 19/20 |
| Recovery torque per motor, +-10 deg | peak 52 N.cm (0.01 s kick), p99 13, rms 5.4; 113 rpm | peak 9.4, p99 7.1, rms 1.8; 105 rpm; pull-out 35.5 at the peak | peak 11.5, p99 5.5, rms 1.4; 100 rpm; pull-out 26.2 |

Why the stepper torque is so much lower than the DC gearmotor numbers: no 19:1 gearbox (the DC rotor inertia reflected through 19:1 is 1.8e-4 kg m2 per motor, about 30x the stepper rotor), the stepper is a velocity source so no voltage-saturation "kick" is needed, and the acceleration is capped.
Note the DC figures come from a voltage-driven model, so the comparison is indicative, not like for like. The stepper loses on noise rejection: tilt and 3 cm hold are noisier, mostly the accelerometer vibration assumption.

What limits recovery (`python sim_step/lim_probe.py`): with the default caps both motors recover +-20 deg starts (nominal). Raising only the acceleration cap to 300 rad/s2 gives 22.5 deg; raising only the speed cap to 300 rpm gives 25 deg;
both give 30 deg. At the next test angle (35 deg, first failure) the 17HS4401 is at margin 0.01 (peak 21.9 N.cm vs 32 available, because pull-out falls with speed) and the 17HS3401S slips 28 poles. So the real kick limit is **speed-dependent pull-out torque** beyond about 25 deg, not the +-10 deg requirement.


## 6. Generated result tables (from `results/tables.md`, 20 randomised runs per case)

Torque columns: per motor, N.cm: peak / p99 / rms / pull-out available at the peak. "Min margin" = 1 - T/pull-out. "Lost-step events" = whole electrical periods lost (4 full steps each).

## Acceptance results (nominal plant, formal seeds)

### 17HS4401

| ID | Test | Result | Key numbers | Torque per motor N.cm: peak / p99 / rms / pull-out at peak | Min margin | Lost-step events |
|---|---|---|---|---|---|---|
| ON | Unpowered +-10 deg must fall | PASS | time to 40 deg 0.22 s (rotor detent torque not modelled) | - | - | - |
| C1.1 | 30 s static balance | PASS | max tilt 1.28 deg, max drift 1.9 cm | 8.8 / 6.5 / 1.8 / 39.1 | 0.78 | 0 |
| C1.2 | 1 m forward + 3 s hold | PASS | travel 1.018 m, hold drift 26.5 mm (v peak 0.053 m/s), max tilt 4.0 deg, dead-reckoning error -0.0 mm | 8.2 / 6.1 / 1.7 / 38.8 | 0.79 | 0 |
| C1.3 | 1 m back + 3 s hold | PASS | travel 0.995 m, hold drift 20.1 mm (v peak 0.079 m/s), max tilt 3.7 deg, dead-reckoning error 0.6 mm | 9.3 / 6.2 / 1.7 / 31.9 | 0.71 | 0 |
| C1.4 | recovery +-10 deg within 10 s | PASS | +10: 0.86 s (travel 13 cm), -10: 0.79 s (travel 12 cm) | 9.4 / 7.1 / 1.8 / 35.5 | 0.72 | 0 |
| GUV.2 | E-stop: balance released, drivers off | PASS | mode after stop STANDBY, stays off True | - | - | - |
| C2.1 | Glove: forward ~0.5 m | PASS | response 0.79 s, travel 0.533 m | 9.0 / 6.0 / 1.7 / 39.1 | 0.77 | 0 |
| C2.2 | Glove: back ~0.5 m | PASS | response 0.77 s, travel -0.491 m | 7.3 / 5.2 / 1.5 / 39.5 | 0.82 | 0 |
| C2.3 | Glove: left ~90 deg | PASS | response 0.24 s, turn 90.0 deg | 9.4 / 7.1 / 1.8 / 39.5 | 0.76 | 0 |
| C2.4 | Glove: right ~90 deg | PASS | response 0.24 s, turn -90.0 deg | 9.4 / 7.1 / 1.8 / 39.5 | 0.76 | 0 |
| C2.5 | Stop: stays in place after all commands | PASS | last 3 s drift 12.0 mm, rotation 0.00 deg; end position error (dead-reckoned vs true) -0.3 mm | 9.2 / 6.1 / 1.7 / 39.2 | 0.76 | 0 |
| GUV.1 | Glove lost (0.3 s): step cut, robot stops | PASS | stopped after 0.306 m (full step 0.5 m) | - | - | - |

### 17HS3401S

| ID | Test | Result | Key numbers | Torque per motor N.cm: peak / p99 / rms / pull-out at peak | Min margin | Lost-step events |
|---|---|---|---|---|---|---|
| ON | Unpowered +-10 deg must fall | PASS | time to 40 deg 0.22 s (rotor detent torque not modelled) | - | - | - |
| C1.1 | 30 s static balance | PASS | max tilt 1.29 deg, max drift 2.9 cm | 7.1 / 4.8 / 1.3 / 27.1 | 0.74 | 0 |
| C1.2 | 1 m forward + 3 s hold | PASS | travel 1.021 m, hold drift 26.3 mm (v peak 0.055 m/s), max tilt 3.5 deg, dead-reckoning error -0.1 mm | 6.6 / 4.7 / 1.2 / 27.3 | 0.76 | 0 |
| C1.3 | 1 m back + 3 s hold | PASS | travel 0.993 m, hold drift 7.3 mm (v peak 0.045 m/s), max tilt 3.5 deg, dead-reckoning error -0.2 mm | 6.8 / 4.9 / 1.3 / 27.2 | 0.75 | 0 |
| C1.4 | recovery +-10 deg within 10 s | PASS | +10: 0.79 s (travel 12 cm), -10: 0.79 s (travel 13 cm) | 11.5 / 5.5 / 1.4 / 26.2 | 0.56 | 0 |
| GUV.2 | E-stop: balance released, drivers off | PASS | mode after stop STANDBY, stays off True | - | - | - |
| C2.1 | Glove: forward ~0.5 m | PASS | response 0.79 s, travel 0.494 m | 5.4 / 4.6 / 1.2 / 27.2 | 0.80 | 0 |
| C2.2 | Glove: back ~0.5 m | PASS | response 0.77 s, travel -0.491 m | 5.4 / 4.5 / 1.2 / 27.4 | 0.80 | 0 |
| C2.3 | Glove: left ~90 deg | PASS | response 0.24 s, turn 90.0 deg | 6.2 / 5.5 / 1.5 / 27.4 | 0.78 | 0 |
| C2.4 | Glove: right ~90 deg | PASS | response 0.24 s, turn -90.0 deg | 6.2 / 5.5 / 1.5 / 27.4 | 0.78 | 0 |
| C2.5 | Stop: stays in place after all commands | PASS | last 3 s drift 0.6 mm, rotation 0.00 deg; end position error (dead-reckoned vs true) -0.3 mm | 6.7 / 4.6 / 1.3 / 27.1 | 0.75 | 0 |
| GUV.1 | Glove lost (0.3 s): step cut, robot stops | PASS | stopped after 0.306 m (full step 0.5 m) | - | - | - |

## Sensitivity (core tests C1.1-C1.4, C2.1-C2.4)

### 17HS4401

| Case | C1.1 | C1.2 | C1.3 | C1.4 | C2.1 | C2.2 | C2.3 | C2.4 | peak T N.cm | min margin | slips |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base (torque x1.0, damp 0.010) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 9.4 | 0.71 | 0 |
| pull-out torque x0.70 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | 9.8 | 0.63 | 0 |
| pull-out torque x0.50 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | 9.0 | 0.51 | 0 |
| pull-out torque x0.35 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 7.8 | 0.36 | 0 |
| rotor damping 0.003 (very low) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 30.7 | 0.20 | 0 |
| rotor damping 0.030 (high) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 9.8 | 0.74 | 0 |
| vibration noise x3 (0.9 m/s2) | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | 10.9 | 0.72 | 0 |
| battery 9.9 V (empty pack) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 9.6 | 0.72 | 0 |
| torque x0.70 + damping 0.003 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 10.3 | 0.60 | 0 |

### 17HS3401S

| Case | C1.1 | C1.2 | C1.3 | C1.4 | C2.1 | C2.2 | C2.3 | C2.4 | peak T N.cm | min margin | slips |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base (torque x1.0, damp 0.010) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 11.5 | 0.56 | 0 |
| pull-out torque x0.70 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | 10.1 | 0.44 | 0 |
| pull-out torque x0.50 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | 8.0 | 0.37 | 0 |
| pull-out torque x0.35 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 8.3 | -0.10 | 0 |
| rotor damping 0.003 (very low) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 13.4 | 0.49 | 0 |
| rotor damping 0.030 (high) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 8.8 | 0.66 | 0 |
| vibration noise x3 (0.9 m/s2) | PASS | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | 8.8 | 0.67 | 0 |
| battery 9.9 V (empty pack) | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | 11.0 | 0.57 | 0 |
| torque x0.70 + damping 0.003 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 8.6 | 0.47 | 0 |

## Largest recovered initial tilt (deg, + / -) and peak torque at that tilt

| Motor | torque scale | + tilt | - tilt | peak T at + (N.cm) | pull-out there |
|---|---|---|---|---|---|
| 17HS3401S | 0.50 | 22.5 | 20.0 | 11.2 | 12.8 |
| 17HS3401S | 0.70 | 20.0 | 20.0 | 10.5 | 17.6 |
| 17HS3401S | 1.00 | 20.0 | 20.0 | 11.4 | 25.0 |
| 17HS4401 | 0.50 | 20.0 | 20.0 | 10.2 | 19.2 |
| 17HS4401 | 0.70 | 20.0 | 20.0 | 14.0 | 25.8 |
| 17HS4401 | 1.00 | 20.0 | 20.0 | 14.9 | 37.6 |

## Robustness (20 randomised runs per case: static 15 s + recovery +-10 + 1 m forward/hold)

### 17HS4401

| Case | static | recovery | 1 m hold <5 cm | 1 m hold <3 cm | worst recovery s | peak T N.cm | min margin | runs with slips | max dead-reckoning err mm |
|---|---|---|---|---|---|---|---|---|---|
| nominal | 20/20 | 20/20 | 20/20 | 18/20 | 1.32 | 15.0 | 0.60 | 0 | 1.2 |
| random | 20/20 | 20/20 | 18/20 | 14/20 | 0.98 | 14.9 | 0.59 | 0 | 1.8 |
| mass-25% | 20/20 | 19/20 | 20/20 | 19/20 | 1.64 | 13.5 | 0.62 | 0 | 1.4 |
| mass+25% | 20/20 | 20/20 | 20/20 | 18/20 | 0.91 | 15.9 | 0.56 | 0 | 1.7 |
| COM-25% | 20/20 | 20/20 | 20/20 | 19/20 | 1.73 | 15.3 | 0.61 | 0 | 1.9 |
| COM+60% | 20/20 | 20/20 | 18/20 | 13/20 | 1.32 | 13.3 | 0.64 | 0 | 2.3 |
| mass+25%/COM+60% | 20/20 | 19/20 | 20/20 | 15/20 | 1.44 | 15.3 | 0.60 | 0 | 1.5 |
| mass-25%/COM-25% | 20/20 | 20/20 | 18/20 | 15/20 | 1.79 | 14.6 | 0.59 | 0 | 1.0 |

### 17HS3401S

| Case | static | recovery | 1 m hold <5 cm | 1 m hold <3 cm | worst recovery s | peak T N.cm | min margin | runs with slips | max dead-reckoning err mm |
|---|---|---|---|---|---|---|---|---|---|
| nominal | 20/20 | 19/20 | 20/20 | 20/20 | 1.73 | 12.6 | 0.51 | 0 | 1.2 |
| random | 20/20 | 20/20 | 19/20 | 19/20 | 0.96 | 12.2 | 0.54 | 0 | 1.5 |
| mass-25% | 20/20 | 20/20 | 20/20 | 17/20 | 1.22 | 12.7 | 0.55 | 0 | 1.2 |
| mass+25% | 20/20 | 20/20 | 20/20 | 19/20 | 0.93 | 13.2 | 0.51 | 0 | 1.4 |
| COM-25% | 20/20 | 20/20 | 20/20 | 18/20 | 1.78 | 12.0 | 0.56 | 0 | 1.5 |
| COM+60% | 20/20 | 19/20 | 19/20 | 16/20 | 1.52 | 11.3 | 0.56 | 0 | 1.3 |
| mass+25%/COM+60% | 20/20 | 19/20 | 20/20 | 16/20 | 1.40 | 11.6 | 0.55 | 0 | 1.8 |
| mass-25%/COM-25% | 20/20 | 20/20 | 20/20 | 17/20 | 0.89 | 11.5 | 0.55 | 0 | 1.1 |

## 7. Plots and traces

* `results/recovery_plus10.png` - pitch, position, wheel rpm and torque vs available pull-out for the +10 deg recovery (both motors).
* `results/run_1m_forward.png` - same for the 1 m forward run with 3 s hold.
* `results/recovery_limit.png` - largest recovered start tilt vs pull-out torque scale (capped by the 200 rpm / 150 rad/s2 limits).
* CSV traces per motor and test in `results/<motor>_c1_*.csv`, `<motor>_c2_glove.csv` (time, true x/v/pitch/yaw, torque L/R in N.cm, pull-out in N.cm, wheel rate, dead-reckoned x, cumulative lost poles).
* `results/summary.tsv` (one line per test and motor), `results/results.json` (everything), `results/tables.md` (the tables above).

## 8. Files and rerun

```
python sim_step/run_all.py            # everything: acceptance, sensitivity, recovery-limit scan, 20-run Monte Carlo, plots
python sim_step/run_all.py --quick    # 5 runs per Monte Carlo case
python sim_step/lim_probe.py          # what limits the recovery angle (acceleration cap / speed cap / torque)
```
Needs Python 3 with numpy, scipy (matplotlib optional for the PNGs). No firmware, `sim/`, `twin/`, `common/`, `cad/`, `tools/` or `docs/` file was modified.

| File | Content |
|---|---|
| `sim_step/params.py` | all constants, motor specs and pull-out curves, plant parameter set |
| `sim_step/plant.py` | wheel-pendulum + DDA step generator + sinusoidal stepper torque with pole slip + IMU model |
| `sim_step/controller.py` | LQR design (acceleration input), tilt filter with acceleration compensation, glove/trapezoid/ref shaping port, torque-aware limits |
| `sim_step/harness.py`, `scenarios.py` | closed loop with glove packets; ports of the acceptance tests and the robustness randomisation |
| `sim_step/run_all.py`, `plots.py`, `lim_probe.py` | driver, plots, recovery-limit probe |

## 9. Open points / what would change the verdict

1. Measure the real pull-out torque at 50-150 rpm for the actual motor + DRV8825 + 11.1 V pack (or find the maker curve). The study passes down to ~0.5 x the assumed curve for the 17HS3401S (about 14 N.cm at standstill).
2. Measure rotor damping/resonance (ring-down of the free rotor with a weight). Very low damping (0.003) is the only case that made torque chatter reach ~31 N.cm.
3. Measure accelerometer vibration with the motors energised and holding; at 3x the assumed level the 1 m +-3 cm hold flips to FAIL for both motors (balance and recovery still pass).
4. Fix `1 m hold` robustness if it matters: lower the accelerometer trust further, add a small position dead band or slower trim, or stiffen the mount of the IMU (these were not tuned to pass the threshold).
5. Set the DRV8825 Vref for peak current: at 1.7 A peak on the 4401 the vector torque is about 28 N.cm (the x0.70 case); 17HS4401 at 1.7 A needs a heat sink; keep 1/16 microstepping and mixed decay.
6. Dead-reckoning cannot detect a lost pole; add a cheap fall-back (e.g. an end-stop or the existing fall detector) if the robot is ever pushed hard.
