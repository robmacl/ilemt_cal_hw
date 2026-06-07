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

| Axis | Name | Encoder Port | Encoder Axis | Stepper Port | Stepper Axis |
|------|------|-------------|-------------|-------------|-------------|
| 0    | X    | 0           | 0           | 4           | 4           |
| 1    | Y    | 1           | 1           | 5           | 5           |
| 2    | Z    | 2           | 2           | 6           | 6           |
| 3    | Rz   | 3           | 3           | 7           | 7           |

**One stepper per connector.** Each stepper uses its own primary FlexAxis port
(pins 1–4), so the stepper axis number equals the stepper port number. The
encoder axis number equals the encoder port number. Encoders on ports 0–3,
steppers on ports 4–7.

> **Why not two steppers per connector?** The P849 *can* put a second
> (N+8) pulse+direction axis on the same connector (pins 11–14), and we
> originally wired X+Y on port 4 and Z+Rz on port 5 that way. It did not work:
> with the primary axis at stepper ATYPE 43 ("pulse+direction *with enable
> output*"), the enable output drives pins 11/12 — the same pins the N+8 axis
> needs for Pulse(N+8) — so the secondary axis emitted no pulses (scope showed
> pins 11/12 static-high). High-density ATYPE 100 frees those pins but is a
> global mode incompatible with the ATYPE-76 encoders we need for the Z index
> (with HD set, the boot banner reported `Stepper Axes : None`). So we moved
> each stepper to its own port. The open question is still out to Trio — see
> [trio_support_inquiry.md](trio_support_inquiry.md) — but one-stepper-per-port
> is the working configuration and the likely permanent one.

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
| 0 (X)  | 16 | -1.5625 | stepper x16 -> microsteps; enc 10000/6400 |
| 1 (Y)  | 16 | -1.5625 | |
| 2 (Z)  | 16 | -1.5625 | |
| 3 (Rz) | 16 | **+1.5625** | encoder counts *opposite* (see cable note) |

The encoder UNITS **sign is per-axis** (`enc_sign[]` in `STARTUP.BAS`): the
goal is only that a positive stepper move produces a positive encoder change,
so the loop and stall detector stay consistent. X/Y/Z need a negative sign;
Rz needs positive because its encoder counts the other way (a +3200 stepper
move gave −3202 on the Rz encoder). The *absolute* direction of any axis
doesn't matter — LabVIEW applies its own sign flips at the control level.

> **⚠ Cable wiring is uncertain (2026-06).** The stage was brought up with
> cables of unknown internal wiring. Continuity checks found differential pairs
> swapped in some connectors but not others (e.g. on X, "RED" lands on pin 4
> = /Dir, while on Rz it matches the colour table). Observed effects:
> - **Stepper Step/Dir polarity differs by axis** — X/Y idle Dir low with
>   positive-going step pulses; Z/Rz idle Dir high with negated pulses. This is
>   in the cabling, not the MC508 (it doesn't change when connectors are
>   swapped at the controller). It is cosmetic: a stepper doesn't care about
>   pulse/dir *polarity*, only edges and relative direction.
> - **Encoder sign** is also affected — Rz ended up with the opposite
>   stepper-vs-encoder sign from X/Y/Z, hence its `+1.5625` above.
>
> Everything is made self-consistent **in software** (`enc_sign[]` and the
> per-axis limit map) rather than by trusting the colour code. The 0V wire
> (WHT/BRN, pin 15) is correct on all, so grounds are fine. **If the cables are
> ever rebuilt, re-verify every axis's encoder sign and Step/Dir, and the
> per-axis `enc_sign`/limit entries can likely return to uniform values.**

**Validated on Z (2026-06-01).** First homing run measured the Z travel
independently on both axes: stepper 126670.9, encoder 126666.9 microsteps —
ratio 0.99997 (~32 ppm, ~4 microsteps over the full range). This confirms the
x16 multiplier, both UNITS values, and the encoder direction. Range ≈ 100.5 mm
(19.8 rev). Use `python homing_monitor.py --range` to read per-axis travel and
the enc/stp ratio after homing.

- **Stepper UNITS = 16:** the internal counter is 16x microsteps, so dividing
  by 16 makes DPOS/MPOS read directly in microsteps. (The leftover fractional
  count you see is the x16 interpolation showing through — harmless.)
- **Encoder UNITS = -1.5625:** scales 10000 enc counts/rev to 6400
  microstep-equivalents/rev. LSB ≈ 0.64 microstep, i.e. *finer* than one step
  — which is what lets the loop resolve sub-step stiction. Negative sign
  reconciles encoder direction with stepper demand.

All four axes share the same stepper UNITS magnitude because translation and
rotation run at the same shaft RPM; the microstep is axis-independent. Only the
encoder sign differs per axis (above).

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
| 3 (Rz) | **input 23** | **input 22** | 22 (enc axis 3) |

FWD_IN and REV_IN are assigned on the stepper axes (to halt motion at
limits). DATUM_IN is assigned on the encoder axes (homing uses the
encoder Z index).

**Rz limits are swapped** (FWD=23, REV=22, the opposite of the wired default)
because the actuator tab reaches the two sensors in the opposite order to the
seek direction. The inputs themselves are unchanged — only which one is
assigned FWD vs REV. (Rz is rotary, so a wrong assignment cruises past both
sensors rather than crashing, but it must still be correct for homing to work.)

## Direction Convention

The goal is only that **positive stepper demand produces a positive encoder
change** on each axis, so the closed loop and stall detector agree. The encoder
UNITS sign achieves this — negative for X/Y/Z, positive for Rz (see the
per-axis table and cable note above). INVERT_STEP has no effect on the P849
(reads back as set but does not change physical direction), so stepper
direction cannot be flipped in software — the sign is always reconciled on the
encoder side, and limit FWD/REV is fixed by swapping the input assignment.

Absolute axis directions are not meaningful here (cabling is non-uniform and
LabVIEW applies its own sign convention); only per-axis self-consistency
matters.

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
- **Coarse homing (limits):** drive the stepper to the negative limit
  (`MOVE(-large)`, REV_IN cancels it), then to the positive limit (FWD_IN
  cancels it), then `MOVEABS` to the geometric midpoint and `DEFPOS(0)` both
  axes there. Hitting both limits is a **self-test**: it proves full travel and
  measures the range (reported in `RANGE_STP`/`RANGE_ENC` VRs).
- **Fine datum (Z index):** from the midpoint, arm `REGIST(20,0,1,0,0)` on the
  encoder axis (channel A, source 1 = Z mark, rising edge), creep the stepper a
  fixed per-axis direction (`seek_dir[]`, all `+1` by default), `wait_mark`
  until `MARK`, read `REG_POS`, and `OFFPOS` **both** axes by `-REG_POS` so the
  index reads zero (encoder is the datum; the stepper tracks 1:1 in microsteps,
  so the same offset keeps DPOS aligned). The capture is hardware-latched at the
  index, so poll latency and creep overshoot don't shift the datum — we do
  **not** move back to the index. The midpoint→index offset is reported per axis
  in `IDX_OFF` (VR 128..131); if it is small (< `IDX_MIN` ≈ 0.2 rev) the seek
  can land on either side of that index between runs, so flip that axis's
  `seek_dir` to `-1` to catch the well-separated index on the other side. No
  index within `IDX_SWEEP` faults `INDEX_NOT_FOUND` (9).

  **Verified on hardware (2026-06, all four axes)** with `index_test.py`: the
  encoder index fires a clean registration mark on X/Y/Z/Rz; consecutive indices
  are exactly one motor rev (6400 microsteps) apart; and re-approaching the same
  index from the same side returns a bit-identical `REG_POS` (0.00 microstep
  peak-to-peak). The index is a sub-microstep-repeatable datum on every axis.
  Re-check anytime with `python index_test.py 0 1 2 3`. (The aliasing seen in
  that script's repeatability phase — `REG_POS` jumping by exactly one rev on
  some approaches — is a host-polling artifact of its re-staging, not datum
  jitter; in `STARTUP.BAS` the seek starts from the fixed midpoint so it always
  catches the same index.)

## MC508 ↔ LabVIEW Interface (VRs)

`STARTUP.BAS` runs at power-up and exposes a small VR contract. Microstep
units throughout. The Python live monitor `homing_monitor.py` polls these
over telnet; LabVIEW uses the same VRs via TrioPC.

**Command (LabVIEW writes):**

| VR  | Name      | Meaning                                                                    |     |
| --- | --------- | -------------------------------------------------------------------------- | --- |
| 100 | HOME_REQ  | axis bitmask to home: bit0=X bit1=Y bit2=Z bit3=Rz (cleared when accepted) |     |
| 101 | CLR_FAULT | write ≠0 to clear the FAULT/ESTOP latch                                    |     |

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
| 128–131 | IDX_OFF | midpoint→index offset per axis (microsteps); flag if small |
| 200–249 | detail | packed ASCII; read with `PRINT VRSTRING(200)` |

**FAULT codes:** 0 OK · 1 NEG_LIMIT_NOT_FOUND · 2 POS_LIMIT_NOT_FOUND ·
4 RANGE_TOO_SMALL · 6 ESTOP_ABORT · 7 TIMEOUT · 8 STALL (stepper demand
outran the shaft encoder — likely a missing/dead limit, hardstop, or collision) ·
9 INDEX_NOT_FOUND (no encoder Z mark within `IDX_SWEEP` of the midpoint)

A fresh `HOME_REQ` auto-clears a stale FAULT latch (when e-stop is released),
so re-pressing Home after a fault simply retries — no explicit `CLR_FAULT`
needed. Seeks are guarded by **encoder stall detection** (abort within ~1 tick
if demand and the shaft encoder diverge by more than ~400 microsteps), with a
generous ~120 s timeout as a secondary backstop. This catches a dead limit
immediately instead of grinding the motor into a hardstop until a timeout.

**STATE codes:** 0 idle · 1 init_done · 10 seek_neg · 11 seek_pos ·
12 to_mid · 13 axis_homed · 14 seek_index · 90 fault · 91 estop_abort

HOMED lives in RAM, so it survives a LabVIEW restart but clears on controller
power-cycle (correct: positions are meaningless after power-up).

## Bring-up Workflow (host tooling)

All host scripts default to the controller at 192.168.0.250 over telnet.

1. **Upload ATYPEs and apply** (one-time / after any ATYPE change):
   ```
   python trio_upload_config.py MC_CONFIG.bas
   ```
   Then **power-cycle** the controller (ATYPE only takes effect on power cycle).
   Verify: `python trio_cmd.py "?ATYPE AXIS(0)" "?ATYPE AXIS(4)"`.

2. **Upload and manually test the homing program** (preferred before autorun):
   ```
   python trio_upload_config.py STARTUP.BAS --run
   ```
   In another shell, watch and drive it:
   ```
   python homing_monitor.py            # watch status
   python homing_monitor.py --home 4   # home Z (bit2); 15 = all, 7 = XYZ
   ```
   Before the first seek on a new axis, confirm its limit switches with a
   no-motion toggle test (trip each switch by hand, watch the marker flip):
   ```
   python homing_monitor.py --inputs
   ```
   `--run` is not persistent — a power-cycle or `EX` stops it. Iterate freely.

3. **Promote to power-up autorun** once validated:
   ```
   python trio_upload_config.py STARTUP.BAS --no-upload --autorun
   ```
   Autorun requires every program on the controller to compile cleanly.

A program cannot be edited while running; the uploader issues `STOP "NAME"`
before editing (use `--halt` to stop all programs if needed).

**One telnet connection at a time.** The MC508 command line accepts a single
telnet session. Run the host tools sequentially, not concurrently — opening a
second connection drops the first. The intended flow is: `--run` uploads and
starts STARTUP then **exits** (releasing the connection), and only *then* do
you run `homing_monitor.py`. `--run` does not move anything: STARTUP inits
(WDOG on, drives energize and hold) and waits for a `HOME_REQ`; the monitor's
`--home N` is what actually triggers motion.

### Changing the controller IP

Set it in `MC_CONFIG.bas` (held in flash, applied at power-up), then
power-cycle and move the PC's NIC to the same subnet:
```
IP_ADDRESS = 192.168.1.250
IP_NETMASK = 255.255.255.0
```
Afterward update the `HOST`/`--host` default in `trio_cmd.py`,
`trio_upload_config.py`, and `homing_monitor.py`.

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

## Boolean Reads: TRUE is -1, not 1

TrioBASIC status flags read back as **-1 for TRUE**, 0 for FALSE — `MARK`,
`IDLE`, and similar. In BASIC `IF MARK AXIS(n) THEN` works naturally (nonzero is
true), but **host code must not test `== 1` or `>= 0.5`** — `-1` fails both.
Compare against nonzero instead (`abs(v) >= 0.5`). This bit the first
`index_test.py` run: a `MARK >= 0.5` check silently missed every `-1`, so a
working index seek looked like a timeout. Digital inputs `IN(n)` are the
exception — they read 1/0, not -1, so the e-stop/limit checks test `< 0.5`.

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

- **Limit inputs are 24V PNP** with an internal 6.8kΩ series resistor and
  opto-isolator. 5V signals require a MIC2981 high-side driver to source
  24V to the input pin.
- **E-stop sense input** is wired with common to +24V giving a "NPN" active low input.
- **Input Com (pin 10) connects to the 24V 0V return**, not to signal
  ground.
