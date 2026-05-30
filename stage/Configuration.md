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
account for this. As a consequence, **DPOS and MPOS on stepper axes are in
these 16x internal units.**

The x16 multiplier has been experimentally confirmed on the P849
(encoder/stepper delta ratio ≈ 1.0 after test moves with these UNITS
values).

| Axis | Units   | Motion/rev | Encoder UNITS | Stepper UNITS |
|------|---------|------------|---------------|---------------|
| 0-2  | mm      | 5.08 mm    | -1968.5       | 20157.5       |
| 3    | degrees | 2 deg      | -5000.0       | 51200.0       |

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

| Parameter | XYZ | Rz | Notes |
|-----------|-----|-----|-------|
| SPEED | 15 mm/s | 5.9 deg/s | ~177 RPM (same shaft speed) |
| ACCEL | 50 mm/s^2 | 19.7 deg/s^2 | 0 to full speed in 0.3s |
| DECEL | 50 mm/s^2 | 19.7 deg/s^2 | |
| CREEP | 1 mm/s | 0.4 deg/s | Homing creep to Z index |

SERVO = OFF on all axes (open-loop stepper; custom closed-loop in BASIC).
WDOG = ON enables the drive relays (global, controlled at runtime).

## Homing (split-axis)

The full homing procedure and axis sequencing are described under "Homing
Procedure" in [../CLAUDE.md](../CLAUDE.md). The split-axis layout (stepper
and encoder on different MC508 axes) imposes these constraints:

- **DATUM(6) cannot be used** when stepper and encoder are on separate
  axes. DATUM expects both the motion output and the encoder Z index on the
  same axis.
- **Simple homing:** Move toward a limit (`MOVE(±large)`, let REV_IN/FWD_IN
  stop it), back off, then `DEFPOS(0)` on both axes.
- **Full Z-index homing** requires custom code: move the stepper axis while
  using `REGIST` on the encoder axis to capture position at the Z mark.

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
