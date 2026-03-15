# MC508 P849 Quirks and Gotchas

Non-obvious behaviors discovered during bring-up. These supplement the
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

- **ATYPE only takes effect after power cycle.** Setting ATYPE in
  MC_CONFIG.bas and uploading requires a full power cycle — not just a
  software reset. Before power cycle, axes will show the default ATYPE 44
  (Analogue Servo).

## INVERT_STEP (P849)

- **INVERT_STEP has no effect on the P849.** The parameter reads back the
  set value (`?INVERT_STEP AXIS(n)` returns 1 after setting ON) but does
  not change the physical step/direction output polarity. Use negative
  UNITS on the encoder axis instead to reconcile sign conventions.

## Stepper Output (ATYPE 43)

- **x16 internal multiplier.** The FlexAxis stepper output counts
  internally at 16x the physical pulse rate. DPOS and MPOS on stepper axes
  are in these 16x units. UNITS must include this factor. Confirmed on
  P849.

- **Step/Dir is RS-422 differential.** For single-ended drivers like the
  KL-4030, connect only the positive output (+) and tie the driver's
  PUL-/DIR- to MC508 0V (pin 15). Do not connect the negative RS-422
  output to avoid reverse-biasing the driver's opto-isolator LED when the
  output is low.

## SPEED / ACCEL / DECEL on Encoder Axes

- **Negative UNITS cause "Parameter out of range" for ACCEL, DECEL, and
  CREEP.** When UNITS is negative (used to flip encoder sign convention),
  setting ACCEL/DECEL/CREEP errors out. Since encoder axes (ATYPE 76) are
  read-only position feedback with no motion commands, these parameters are
  not needed and should not be set.

## Limit Switches and FWD_IN / REV_IN

- **FWD_IN/REV_IN are active-low** (trigger when input reads 0). The raw
  sensor polarity of the stage limit switches already matches this
  convention (1 = away from limit, 0 = at limit), so INVERT_IN is not
  needed.

- **Swapping FWD_IN/REV_IN is dangerous.** If limit assignments don't
  match the physical direction, the motor will drive into the limit switch
  with no protection. Always verify which input triggers at which end
  before relying on limits for homing.

- **Any input 0-31 can be used for FWD_IN/REV_IN/DATUM_IN.** They do not
  need to be registration inputs (0-7). Registration is only needed for
  hardware position capture (REGIST command).

## KL-4030 Driver ENA Input

- **ENA is active-high DISABLE, not enable.** Current through the ENA
  opto-isolator disables the motor driver. The WDOG relay circuit must
  be wired so that ENA is de-energized when drives should be active.
  Current wiring is inverted (e-stop pressed = motor enabled).

## MC508 Inputs

- **All inputs are 24V PNP** with internal 6.8kΩ series resistor and
  opto-isolator. 5V signals require a MIC2981 high-side driver to source
  24V to the input pin.

- **Input Com (pin 10) connects to 24V 0V return**, not to signal ground.

## Homing in Split-Axis Setup

- **DATUM(6) cannot be used** when stepper and encoder are on separate
  axes. DATUM expects both motion output and encoder Z index on the same
  axis.

- **Simple homing:** Move toward limit (MOVE(±999), let REV_IN/FWD_IN
  stop it), back off, DEFPOS(0) both axes.

- **Full Z-index homing** would require custom code: move stepper while
  using REGIST on the encoder axis to capture position at the Z mark.

## Telnet Communication

- **The `>>` prompt signals command completion.** Use this for
  response-complete detection rather than fixed timeouts. Commands are
  CR-terminated. No authentication required.

- **The controller echoes commands** back over telnet. Filter these from
  responses along with the `>>` prompt lines.
