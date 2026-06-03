# Trio Support Inquiry — MC508 P849 N+8 pulse output vs. primary enable output

## Question

On an MC508 P849, can a secondary pulse+direction axis (N+8, e.g. axis 12 on
the port-4 connector) output step pulses **while the primary axis (axis 4) on
the same connector is configured as a pulse+direction stepper (ATYPE 43)** —
and if so, how is that pin function selected? We also need to keep the
encoder **Z index** available on the encoder axes (for index homing), so we
want to avoid any mode that drops the Z channel.

## Hardware / firmware

- Controller: **MC508 P849** (servo version, axes 8–15 available as pulse output)
- Firmware (`VERSION`): **2.0316**
- FPGA (`FPGA_VERSION`): **11**
- `FEATURE_ENABLE`: 8388608

## Configuration

Per stage axis we use one encoder axis (ATYPE 76) + one stepper axis (ATYPE 43):

| Stage axis | Encoder axis | Stepper axis | Stepper port | Path |
|-----------|--------------|--------------|--------------|------|
| X  | 0 | 4  | port 4 | primary (n)   |
| Y  | 1 | 12 | port 4 | secondary (n+8) |
| Z  | 2 | 5  | port 5 | primary (n)   |
| Rz | 3 | 13 | port 5 | secondary (n+8) |

The secondary stepper outputs are wired to connector pins **11/12 = Pulse(n+8),
13/14 = Dir(n+8)** per the MC508 FlexAxis pinout (P849 column).

## Symptom

- Primary stepper axes **4 and 5 work** (pulses out pins 1–4, motors move,
  shaft encoders track ~1.0 ratio — validated).
- Secondary axes **12 and 13 do not output pulses.** `DPOS` advances on a
  `MOVE`/`FORWARD`, `AXIS_ENABLE=1`, `AXISSTATUS=0`, but **no step pulses
  appear** on pins 11/13. Scope shows pins **11/12 driven statically HIGH**
  (no toggling) — i.e. they appear to be driving the **Enable(n) output** of
  the primary ATYPE-43 axis, which shares those same pins per the manual's
  pinout table.
- Both n+8 axes (12 and 13) fail identically; motors/encoders are confirmed
  good by swapping cables at the stage end.

## What we tried

- Confirmed ATYPE: 4/5/12/13 = 43, encoders 0–3 = 76 (survives power cycle).
- `AXIS_Z_OUTPUT AXIS(4) = 0` (live, then move axis 12): no change — pins 11/12
  stay high, no pulses. (Our reading: this only lets AXIS_ENABLE drive the
  enable output; it does not re-mux the pin to Pulse(n+8).)

## Specific questions

1. Is there a parameter / ATYPE / FPGA program that makes pins 11–14 carry
   `Pulse(n+8)`/`Dir(n+8)` **while the primary axis remains a working ATYPE-43
   stepper**? The manual shows the pin mapping but not what selects it.
2. Does using the n+8 pulse output **require the primary axis to use an ATYPE
   without the enable output** (which standard ATYPE supports plain
   pulse+direction with no enable and no Z consumption on pins 11–14)?
3. For the MC508, what `FPGA_PROGRAM` variants are available, and do any free
   the n+8 pins **without losing the encoder Z index** on the 0–3 encoder axes?
   (`FPGA_PROGRAM(-1)` returns "Operand expected" from the command line on this
   unit — what's the correct way to list variants?)
4. Is the High-Density mode (ATYPE 100–104) the only way to get all 16 pulse
   axes, and does it indeed drop the Z channel as the manual states?

## Our fallback (no answer needed, just FYI)

Ports 6 and 7 are unused (came up as default servo). If n+8 can't coexist with
a primary stepper while keeping Z, we'll move the Y and Rz stepper cables to
ports 6/7 as primary ATYPE-43 axes (pins 1–4), keeping all four encoder Z
indexes. We'd prefer the n+8 approach if it's supported, to save the rewire.
