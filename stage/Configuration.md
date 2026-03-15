# Stage Configuration
The MC 508 is connected at 192.168.0.250

For initial single axis testing the Z axis connected.
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
account for this.

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
but does not change physical direction).

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
