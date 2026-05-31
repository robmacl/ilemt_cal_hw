# Stage Configuration & MC508 Quirks

The MC508 is connected at 192.168.0.250.

This is the authoritative reference for the motion-controller configuration
(axis mapping, units, I/O, motion parameters, homing) and for the
non-obvious controller behaviours ("quirks") discovered during bring-up.
Physical/electrical wiring is documented separately in
[stage_wiring.md](stage_wiring.md).

For initial single-axis testing the Z axis was connected first.

## Terminology

- **Axis** (or "axis N") — a stage motion axis. Numbered 0–3 to match the
  encoder feedback port, so "axis 0" identifies both the stage axis and
  the MC508 encoder axis.
- **Encoder axis** — the MC508 axis configured as ATYPE 76 (encoder input
  with Z index). Same number as the stage axis.
- **Stepper axis** — the MC508 axis configured as ATYPE 43 (pulse+direction
  output). Different number from the stage axis.
- **Port** — a physical MC508 20-pin MDR connector (0–7).

Each axis uses two MC508 axes: an encoder axis for position feedback and a
stepper axis for motor drive.

## Axes

| Axis | Name | Encoder Port | Encoder Axis | Stepper Port | Stepper Axis | Driver Path |
|------|------|-------------|-------------|-------------|-------------|-------------|
| 0    | X    | 0           | 0           | 4           | 4           | DRV_A       |
| 1    | Y    | 1           | 1           | 4           | 12          | DRV_B       |
| 2    | Z    | 2           | 2           | 5           | 5           | DRV_A       |
| 3    | Rz   | 3           | 3           | 5           | 13          | DRV_B       |

DRV_A is the primary axis (N) on a stepper port; DRV_B is the secondary
axis (N+8) on the P849 dual-axis connector. X and Z happen to be on the
DRV_A path, so the stepper axis numbers don't follow the stage axis order.

## Hardware

- **Encoder:** US Digital E6-2500-250-IE-D-E-D-B — 2500 CPR (cycles/rev)
- **Stepper:** KL23H278-28-4B — NEMA 23, 200 full steps/rev (1.8 deg)
- **Driver:** KL-4030 set to 1/32 microstepping
- **Lead screw:** 0.2 in/rev (5.08 mm/rev) for XYZ, 2 deg/rev for Rz

## Counts and Units

| Parameter | Value | Derivation |
|-----------|-------|------------|
| Encoder counts/rev | 10,000 | 2500 CPR x 4 (quadrature) |
| Stepper microsteps/rev | 6,400 | 200 full steps x 32 |
| Stepper internal counts/rev | 102,400 | 6,400 x 16 (FlexAxis multiplier) |

The MC508 FlexAxis stepper output works internally at 16x finer resolution
than the actual output pulse rate, for smoother pulse timing. UNITS must
account for this. The x16 multiplier has been experimentally confirmed on
the P849 (encoder/stepper delta ratio ≈ 1.0 after test moves).

### Software unit = microsteps (all axes)

Both axes report in **microsteps** (6400/rev), the stepper's native quantum
and the same convention the existing LabVIEW code uses. This is deliberate:
the closed-loop control treats the encoder as truth and the stepper as an
actuator, nudging the stepper by the encoder-measured error. Keeping a single
unit means the error you read (encoder) is directly the increment you command
(stepper) — no tick conversion. The encoder/stepper count ratio (10000/6400 =
1.5625) is absorbed once into the encoder UNITS and never appears again.

| Axis | Stepper UNITS | Encoder UNITS | Notes |
|------|---------------|---------------|-------|
| all (0-3) | 16 | -1.5625 | stepper x16 -> microsteps; enc 10000/6400, sign flips dir |

- **Stepper UNITS = 16:** the internal counter is 16x microsteps, so dividing
  by 16 makes DPOS/MPOS read directly in microsteps. (The leftover fractional
  count you see is the x16 interpolation showing through — harmless.)
- **Encoder UNITS = -1.5625:** scales 10000 enc counts/rev to 6400
  microstep-equivalents/rev. LSB ≈ 0.64 microstep, i.e. *finer* than one step
  — which is what lets the loop resolve sub-step stiction. Negative sign
  reconciles encoder direction with stepper demand.

All four axes share the same UNITS because translation and rotation run at the
same shaft RPM; the microstep is axis-independent.

**Physical units (mm, degrees) are a presentation/output conversion at the
LabVIEW boundary**, applied only where physical position is needed (displays,
calibration model input):

| Axis | microsteps -> physical | per rev |
|------|------------------------|---------|
| 0-2 (XYZ) | x 5.08 / 6400 mm | 5.08 mm |
| 3 (Rz)    | x 2 / 6400 deg   | 2 deg   |

## Limit Switch Inputs

Limit switches are on the encoder port digital inputs (ATYPE 76, pins 9
and 20). INVERT_IN is NOT needed — the raw sensor polarity matches
Trio's active-low convention (sensor reads 1 when away from limit, 0
at limit, and FWD_IN/REV_IN/DATUM_IN all trigger on 0).

| Axis | Pos Limit (FWD_IN) | Neg Limit (REV_IN) | DATUM_IN |
|------|--------------------|--------------------|----------|
| 0 (X) | input 16 | input 17 | 17 (enc axis 0) |
| 1 (Y) | input 18 | input 19 | 19 (enc axis 1) |
| 2 (Z) | input 20 | input 21 | 21 (enc axis 2) |
| 3 (Rz) | input 22 | input 23 | 23 (enc axis 3) |

FWD_IN and REV_IN are assigned on the stepper axes (to halt motion at
limits). DATUM_IN is assigned on the encoder axes (homing uses the
encoder Z index).

## Direction Convention

The encoder counts in the opposite direction to the stepper. The encoder
UNITS are negated so that positive stepper demand produces positive encoder
position change. INVERT_STEP has no effect on the P849 (reads back as set
but does not change physical direction), so the sign is reconciled with
negative encoder UNITS instead.

For the Z axis, positive = down, negative = up.

## Motion Parameters

Set on the stepper axes at power-up by `STARTUP.BAS`, in microstep units.
(Same shaft RPM for all axes, so the microstep values are identical; the
mm- and deg-equivalents differ only because the per-rev distance differs.)

| Parameter | microsteps | XYZ equiv | Rz equiv | Notes |
|-----------|-----------|-----------|----------|-------|
| SPEED | 18900 /s   | ~15 mm/s   | ~5.9 deg/s   | ~177 RPM |
| ACCEL | 63000 /s^2 | ~50 mm/s^2 | ~19.7 deg/s^2 | 0→full in ~0.3s |
| DECEL | 63000 /s^2 | ~50 mm/s^2 | ~19.7 deg/s^2 | |
| HOME_SPEED (CREEP) | 6300 /s | ~5 mm/s | ~2 deg/s | slow limit approach |

SERVO = OFF on all axes (open-loop stepper; closed-loop position correction
runs in LabVIEW around the encoder). WDOG = ON enables the drive relays;
`STARTUP.BAS` turns it on after configuring the axes.

## Closed-Loop Control Model

The encoder is mounted on the **motor shaft** (not the load); the
leadscrew/worm is not back-drivable. Control philosophy:

- **Encoder = truth, stepper = actuator.** LabVIEW reads the encoder, commands
  an incremental stepper move of (target − encoder), and repeats until within
  tolerance. The stepper's absolute zero does not matter — only the encoder is
  homed.
- **Backlash is handled by always approaching a setpoint from the same side**
  (mechanically aided by an anti-backlash nut and a stiff coupler). The fielded
  creep sequence — cross to −100 steps, forward to −15, then 80%-of-remaining
  moves until within ±3 steps, overshoot >+3 ⇒ back to −100 and retry — lives
  in **LabVIEW** (for visibility and to reuse the existing stats displays).
- **Tracking-error / stall detection** is a safety backstop in LabVIEW: a fault
  only if the encoder lags the commanded stepper move by **2–3 whole steps
  (≈64–96 microsteps)**, well above normal microstep stiction.
- e-stop only disables the driver; the shaft holds and the encoder keeps its
  count, so a point-to-point move is recoverable after e-stop by re-reading the
  encoder. Only a controller power-cycle invalidates position (clears HOMED).

## Homing (split-axis)

Sequencing and intent are in [../CLAUDE.md](../CLAUDE.md) ("Homing
Procedure"). Implemented in `STARTUP.BAS`. Order: **X, Y, Z then Rz last**
(Rz can swing attached fixtures). The split-axis layout (stepper and encoder
on different MC508 axes) means:

- **`DATUM(n)` cannot be used** — it expects the motion output and the encoder
  Z index on the *same* axis.
- **Current (simple) homing — no Z index yet:** drive the stepper to the
  negative limit (`MOVE(-large)`, REV_IN cancels it), then to the positive
  limit (FWD_IN cancels it), then `MOVEABS` to the geometric midpoint and
  `DEFPOS(0)` both axes there. Hitting both limits is a **self-test**: it
  proves full travel and measures the range (reported in `RANGE_STP`/
  `RANGE_ENC` VRs).
- **Future Z-index homing** (finer, repeatable datum) would add: after a limit,
  `REGIST` on the encoder axis while the stepper creeps, `WAIT UNTIL MARK`,
  read `REG_POS`, and `OFFPOS`/`DEFPOS` the encoder at the index. The
  REGIST/MARK/REG_POS path is verified; deferred until simple homing is
  validated on hardware.

## MC508 ↔ LabVIEW Interface (VRs)

`STARTUP.BAS` runs at power-up and exposes a small VR contract. Microstep
units throughout. The Python live monitor `homing_monitor.py` polls these
over telnet; LabVIEW uses the same VRs via TrioPC.

**Command (LabVIEW writes):**

| VR | Name | Meaning |
|----|------|---------|
| 100 | HOME_REQ | axis bitmask to home: bit0=X bit1=Y bit2=Z bit3=Rz (cleared when accepted) |
| 101 | CLR_FAULT | write ≠0 to clear the FAULT/ESTOP latch |

**Status (LabVIEW / monitor polls):**

| VR | Name | Meaning |
|----|------|---------|
| 110 | HOMED | axis bitmask of homed axes; persists until power cycle |
| 111 | BUSY | 1 while homing |
| 112 | ESTOP | 1 if e-stop input currently asserted (live) |
| 113 | FAULT | fault code (0 = OK) |
| 114 | FAULT_AXIS | axis (0–3) the fault occurred on |
| 115 | STATE | coarse progress code (live monitor) |
| 116 | CUR_AXIS | axis currently being homed |
| 120–123 | RANGE_STP | measured stepper travel per axis (microsteps) |
| 124–127 | RANGE_ENC | measured encoder travel per axis (microsteps) |
| 200–249 | detail | packed ASCII; read with `PRINT VRSTRING(200)` |

**FAULT codes:** 0 OK · 1 NEG_LIMIT_NOT_FOUND · 2 POS_LIMIT_NOT_FOUND ·
4 RANGE_TOO_SMALL · 6 ESTOP_ABORT · 7 TIMEOUT

**STATE codes:** 0 idle · 1 init_done · 10 seek_neg · 11 seek_pos ·
12 to_mid · 13 axis_homed · 90 fault · 91 estop_abort

HOMED lives in RAM, so it survives a LabVIEW restart but clears on controller
power-cycle (correct: positions are meaningless after power-up).

**E-stop sense:** wired to digital input **0** (terminal **XA0**, expansion A
terminal 0). The input reads **ON when the e-stop is released** ("out") and
OFF when pressed, **independent of the WDOG relay state**. This is fail-safe:
a broken wire reads OFF and is treated as pressed. `STARTUP.BAS` treats
`IN(0)=OFF` as e-stop asserted (sets `ESTOP` VR, aborts homing).

---

# Quirks and Gotchas

Non-obvious behaviours discovered during bring-up. These supplement the
official Trio documentation.

## Telnet Command Line

- **`REV_JOG` / `FWD_JOG` are program-only commands.** They cannot be
  issued from the telnet command line or via Execute(). Use
  `MOVE(±large_value)` instead and let FWD_IN/REV_IN stop motion at the
  limit.

- **`JOG(speed)` fails on the command line** with "Variables not permitted".
  Same workaround as above.

- **`DPOS` and `MPOS` are read-only** on the command line. Cannot assign
  with `DPOS AXIS(n) = 0`. Use `DEFPOS(0) AXIS(n)` instead, which sets
  both DPOS and MPOS to the given value.

- **The `>>` prompt signals command completion.** Use this for
  response-complete detection rather than fixed timeouts. Commands are
  CR-terminated. No authentication required.

- **The controller echoes commands** back over telnet. Filter these from
  responses along with the `>>` prompt lines.

## ATYPE Only Takes Effect After Power Cycle

Setting ATYPE in MC_CONFIG.bas and uploading requires a full power cycle —
not just a software reset. Before the power cycle, axes will show the
default ATYPE 44 (Analogue Servo).

## Stepper Output (ATYPE 43)

- **x16 internal multiplier.** See "Counts and Units" above — DPOS/MPOS on
  stepper axes are in 16x internal units and UNITS must include the factor.

- **Step/Dir is RS-422 differential.** For single-ended drivers like the
  KL-4030, connect only the positive output (+) and tie the driver's
  PUL-/DIR- to MC508 0V (pin 15). Do not connect the negative RS-422
  output, to avoid reverse-biasing the driver's opto-isolator LED when the
  output is low.

## Encoder Axes (ATYPE 76)

- **Don't set SPEED/ACCEL/DECEL/CREEP with negative UNITS.** When UNITS is
  negative (used to flip the encoder sign convention), setting
  ACCEL/DECEL/CREEP errors out with "Parameter out of range". Encoder axes
  are read-only position feedback with no motion commands, so these
  parameters are not needed and should not be set.

## Limit Switches and FWD_IN / REV_IN

- **Swapping FWD_IN/REV_IN is dangerous.** If limit assignments don't
  match the physical direction, the motor will drive into the limit switch
  with no protection. Always verify which input triggers at which end
  before relying on limits for homing.

- **Any input 0-31 can be used for FWD_IN/REV_IN/DATUM_IN.** They do not
  need to be registration inputs (0-7). Registration is only needed for
  hardware position capture (the REGIST command).

(Polarity: FWD_IN/REV_IN are active-low — see "Limit Switch Inputs" above.)

## KL-4030 Driver ENA Input

- **ENA is active-high DISABLE, not enable.** Current through the ENA
  opto-isolator disables the motor driver. The WDOG relay circuit must
  be wired so that ENA is de-energized when drives should be active.
  Current wiring is inverted (e-stop pressed = motor enabled).

## MC508 Inputs

- **All inputs are 24V PNP** with an internal 6.8kΩ series resistor and
  opto-isolator. 5V signals require a MIC2981 high-side driver to source
  24V to the input pin.

- **Input Com (pin 10) connects to the 24V 0V return**, not to signal
  ground.
