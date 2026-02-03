# Stage Wiring Documentation

## Overview

This document tracks the wiring of the existing ILEMT calibration stage cables,
originally terminated for the NI UMI-7774 breakout interface, and their adaptation
to the Trio MC508 P849 motion controller.

## NI UMI-7774 Feedback Connector (DB-25 Female on UMI)

The stage cables plug into the per-axis **Feedback** connector on the UMI-7774.
This is a 25-pin D-SUB. The cable side is a DB-25 male connector.

### UMI-7774 Feedback Connector Pinout (from NI manual)

| Pin | Signal              | Isolated | Notes                          |
|-----|---------------------|----------|--------------------------------|
| 1   | Encoder Phase A     | No       | Differential +                 |
| 2   | Encoder Phase B     | No       | Differential +                 |
| 3   | Encoder Index       | No       | Differential +                 |
| 4   | +5V Output          | No       | Encoder power (shared 1A max)  |
| 5   | Reserved            | No       |                                |
| 6   | Reserved            | No       |                                |
| 7   | Reserved            | No       |                                |
| 8   | +5V Output          | No       | Encoder power (shared 1A max)  |
| 9   | NC                  | No       |                                |
| 10  | Forward Limit       | Yes      | Optically isolated sinking input |
| 11  | Home Input          | Yes      | Optically isolated sinking input |
| 12  | Reverse Limit       | Yes      | Optically isolated sinking input |
| 13  | Viso (Output)       | Yes      | Power for isolated I/O (5-30V) |
| 14  | Encoder Phase A-    | No       | Differential -                 |
| 15  | Encoder Phase B-    | No       | Differential -                 |
| 16  | Encoder Index-      | No       | Differential -                 |
| 17  | Digital Ground      | No       |                                |
| 18  | Digital Ground      | No       |                                |
| 19  | Digital Ground      | No       |                                |
| 20  | Digital Ground      | No       |                                |
| 21  | NC                  | No       |                                |
| 22  | Ciso                | Yes      | Isolated common                |
| 23  | Ciso                | Yes      | Isolated common                |
| 24  | Ciso                | Yes      | Isolated common                |
| 25  | Ciso                | Yes      | Isolated common                |

### Signals Present on Cable

The stage cable carries signals for one axis:
- **Encoder**: Differential quadrature (A/A-, B/B-, Z/Z-) + power (+5V, GND)
- **Limit switches**: 3 opto-interrupters (Forward, Home, Reverse)
  - These are powered from Viso/Ciso (isolated supply, 5-30V)
  - Output goes to the optically isolated sinking inputs on the UMI
  - The opto-interrupters need +V supply and ground, and have a digital output
  - If open-collector output: Viso -> pull-up -> signal input pin, output sinks to Ciso
  - If sourcing (PNP-style): Viso powers sensor, output drives input pin, return to Ciso

### Populated Pins on DB-25 (from connector photos)

From the photos of the DB-25 male connector (stage/Pics/PXL_20260106_162751644.jpg
and PXL_20260106_163028589.jpg), the following pins have contacts populated.
Two gray cables enter the DB-25 shell.

**Top row (pins 1-13):**
- Pins 1, 2, 3, 4: populated (encoder signals + power)
- Pins 5, 6, 7, 8, 9: empty
- Pins 10, 11, 12, 13: populated (limits/home + Viso)

**Bottom row (pins 14-25):**
- Pins 14, 15, 16, 17: populated (encoder differential- + ground)
- Pins 18, 19, 20, 21: empty
- Pins 22, 23: populated (Ciso)
- Pins 24, 25: empty

#### Summary of Wired Pins

| DB-25 Pin | UMI-7774 Signal     | Group              |
|-----------|---------------------|--------------------|
| 1         | Encoder Phase A     | Encoder (cable 1)  |
| 2         | Encoder Phase B     | Encoder (cable 1)  |
| 3         | Encoder Index (Z)   | Encoder (cable 1)  |
| 4         | +5V Output          | Encoder (cable 1)  |
| 14        | Encoder Phase A-    | Encoder (cable 1)  |
| 15        | Encoder Phase B-    | Encoder (cable 1)  |
| 16        | Encoder Index-      | Encoder (cable 1)  |
| 17        | Digital Ground      | Encoder (cable 1)  |
| 10        | Forward Limit       | Limits (cable 2)   |
| 11        | Home Input          | Limits (cable 2)   |
| 12        | Reverse Limit       | Limits (cable 2)   |
| 13        | Viso (Output)       | Limits (cable 2)   |
| 22        | Ciso                | Limits (cable 2)   |
| 23        | Ciso                | Limits (cable 2)   |

Total: 14 pins populated, matching the ~14 wires visible in the shell.

**Cable 1 (encoder, 8 wires):** Differential A/B/Z quadrature encoder with +5V
power and ground.

**Cable 2 (limits, 6 wires):** Three opto-interrupter signals (fwd/home/rev)
powered by the UMI's isolated supply (Viso/Ciso). Two Ciso pins are used,
likely one shared return and one spare, or separate returns for sensor groups.

### MC508 SCSI Cable Wire Colors (20-pin MDR)

From handwritten notes (stage/Pics/PXL_20260106_162549339.jpg):

| MDR Pin | Wire Color      | MC508 Signal    |
|---------|-----------------|-----------------|
| 1       | BLK             | Enc A+          |
| 2       | BRN             | /Enc A          |
| 3       | RED             | Enc B+          |
| 4       | ORN             | /Enc B          |
| 5       | YEL             | +5V Enc         |
| 6       | GRN             | N/C             |
| 7       | BLU             | WDOG+           |
| 8       | PUR             | WDOG-           |
| 9       | GRY             | Input A+        |
| 10      | WHT             | Input Com       |
| 11      | LTGRN           | Enc Z+          |
| 12      | LTBLU           | /Enc Z          |
| 13      | PINK            | Dir+  / Pulse+  |
| 14      | WHT/BLK         | /Dir  / /Pulse  |
| 15      | WHT/BRN         | 0V Enc          |
| 16      | WHT/RED         | N/C             |
| 17      | WHT/ORN         | VOUT+           |
| 18      | WHT/YEL         | VOUT-           |
| 19      | WHT/GRN         | N/C             |
| 20      | WHT/BLU         | Input B+        |

Note: Pins 13/14 are labeled "Dir+5" / "/Dir+5" in the notes. On the ATYPE 43
(stepper) port these are Pulse+/Pulse- (pins 1-2) or Dir+/Dir- (pins 3-4)
depending on configuration. On the ATYPE 76 (encoder) port, pins 13/14 don't
exist — the encoder port uses pins 1-4 for encoder A/B.

## MC508 Input Compatibility

### Encoder Signals — Compatible

The encoder outputs (RS-422 differential, 5V) connect directly to the MC508
flex axis encoder inputs. The MC508 encoder inputs accept differential RS-422
signals and provide +5V encoder power (100mA max per port). No adaptation needed.

### Limit Switch Signals — NOT Compatible

**Problem:** The opto-interrupter limit switches are sourcing (PNP) type, powered
from 5V (Viso on the UMI-7774). The MC508 digital inputs are ALL 24V
opto-isolated with a 6.8kΩ series resistor.

At 5V input: (5V - 1.2V) / 6.8kΩ ≈ 0.56 mA — far too low to turn on the
opto-isolator (needs ~3 mA, requiring ~21.6V minimum).

**The 5V opto-interrupter outputs cannot directly drive MC508 inputs.**

### Solution: ULN2003A Darlington Array

Use a ULN2003A to interface the 5V opto-interrupter outputs to the MC508 24V
inputs. The ULN2003A has 7 Darlington channels with integrated base resistors,
so it can be driven directly from 5V logic. Each channel sinks up to 500mA
(far more than needed). The MC508 PNP inputs source current through the 6.8kΩ
resistor; the ULN2003A sinks this to ground.

**Circuit per limit switch:**
- Opto-interrupter 5V output → ULN2003A input
- ULN2003A output → MC508 digital input
- MC508 input is internally pulled to 24V through 6.8kΩ
- ULN2003A common emitter → ground (shared with MC508 0V)

One ULN2003A handles all limit switches for all 3 axes (6 channels used of 7).

## MC508 Flex Axis Connector Pinout (20-pin MDR)

### ATYPE 43 — Stepper Pulse+Direction Output (P849 with axis N+8)

| Pin | Signal          | Notes                              |
|-----|-----------------|-------------------------------------|
| 1   | Pulse(N)+       | Differential step output, axis N    |
| 2   | /Pulse(N)       |                                     |
| 3   | Dir(N)+         | Differential direction, axis N      |
| 4   | /Dir(N)         |                                     |
| 5   | +5V             | Encoder power (100mA max)           |
| 7   | WDOG+           | Watchdog SSR (24V/100mA max, ~25Ω)  |
| 8   | WDOG-           |                                     |
| 9   | Input 16+n*2    | Digital input (24V, PNP)            |
| 10  | Input Com       | Input common                        |
| 11  | Pulse(N+8)+     | Differential step output, axis N+8  |
| 12  | /Pulse(N+8)     |                                     |
| 13  | Dir(N+8)+       | Differential direction, axis N+8    |
| 14  | /Dir(N+8)       |                                     |
| 15  | 0V              | Digital ground                      |
| 17  | VOUT+           | Analog servo output (±10V DAC)      |
| 18  | VOUT-           | NOT a 24V power supply              |
| 20  | Input 17+n*2    | Digital input (24V, PNP)            |

Note: On P849, pins 11-14 carry axis N+8 pulse/direction instead of
enable/̅enable. The WDOG relay (pins 7/8) serves as the enable mechanism.

### ATYPE 76 — Encoder Input

| Pin | Signal          | Notes                        |
|-----|-----------------|------------------------------|
| 1   | Encoder A+      | Differential quadrature      |
| 2   | /Encoder A      |                              |
| 3   | Encoder B+      | Differential quadrature      |
| 4   | /Encoder B      |                              |
| 5   | +5V             | Encoder power (100mA max)    |
| 9   | Input 16+n*2    | Digital input (24V, PNP)     |
| 11  | Encoder Z+      | Index pulse                  |
| 12  | /Encoder Z      |                              |
| 15  | 0V              | Digital ground               |
| 20  | Input 17+n*2    | Digital input (24V, PNP)     |

The 2 digital inputs per ATYPE 76 port are sufficient — only forward and
reverse limits are needed (home input is not used).

## Signals to Connect (per axis)

| DB-25 Pin | UMI-7774 Signal  | MC508 Destination              | Notes              |
|-----------|------------------|--------------------------------|--------------------|
| 1         | Encoder A+       | ATYPE 76 port pin 1 (Enc A+)  | Direct             |
| 14        | Encoder A-       | ATYPE 76 port pin 2 (/Enc A)  | Direct             |
| 2         | Encoder B+       | ATYPE 76 port pin 3 (Enc B+)  | Direct             |
| 15        | Encoder B-       | ATYPE 76 port pin 4 (/Enc B)  | Direct             |
| 3         | Encoder Z+       | ATYPE 76 port pin 11 (Enc Z+) | Direct             |
| 16        | Encoder Z-       | ATYPE 76 port pin 12 (/Enc Z) | Direct             |
| 4         | +5V              | ATYPE 76 port pin 5 (+5V)     | Encoder power from MC508 |
| 17        | Digital Ground   | ATYPE 76 port pin 15 (0V)     | Encoder ground     |
| 10        | Forward Limit    | ULN2003A in → out to input pin 9  | Via level shifter |
| 12        | Reverse Limit    | ULN2003A in → out to input pin 20 | Via level shifter |
| 13        | Viso             | External 5V supply             | Opto-interrupter power |
| 22, 23    | Ciso             | External 5V ground             | Opto-interrupter return |
| 11        | Home Input       | Not connected                  | Not used           |

### Power Supplies

- **Encoders**: Powered from MC508 +5V on each ATYPE 76 port (pin 5, 100mA max).
  Encoder ground returns to MC508 0V (pin 15). Using the MC508's own encoder
  power avoids common-mode noise on the differential signals.
- **Opto-interrupters (limit switches)**: Powered from existing external 5V supply
  (previously used for UMI-7774 Viso). Ground shared with ULN2003A common emitter
  and MC508 0V.

## Adapter Wirelist (per axis)

DB-25 (stage cable) → MC508 SCSI cable, via adapter. Encoder port (ATYPE 76).

| DB-25 Pin | Signal       | MC508 MDR Pin | SCSI Wire   | Notes                  |
|-----------|--------------|---------------|-------------|------------------------|
| 1         | Enc A+       | 1             | BLK         | Direct                 |
| 14        | Enc A-       | 2             | BRN         | Direct                 |
| 2         | Enc B+       | 3             | RED         | Direct                 |
| 15        | Enc B-       | 4             | ORN         | Direct                 |
| 3         | Enc Z+       | 11            | LTGRN       | Direct                 |
| 16        | Enc Z-       | 12            | LTBLU       | Direct                 |
| 4         | +5V          | 5             | YEL         | MC508 encoder power    |
| 17        | Dig Gnd      | 15            | WHT/BRN     | Encoder ground         |
| 10        | Fwd Limit    | —             | —           | To ULN2003A input      |
| 12        | Rev Limit    | —             | —           | To ULN2003A input      |
| 13        | Viso         | —             | —           | To external 5V supply  |
| 22, 23    | Ciso         | —             | —           | To external 5V ground  |
| 11        | Home         | —             | —           | Not connected          |

ULN2003A outputs connect to MC508 SCSI cable:

| ULN2003A Out | MC508 MDR Pin | SCSI Wire | MC508 Input   |
|--------------|---------------|-----------|---------------|
| Fwd Limit    | 9             | GRY       | Input 16+n*2  |
| Rev Limit    | 20            | WHT/BLU   | Input 17+n*2  |

ULN2003A common emitter → MC508 Input Com (pin 10, WHT) for 24V return path.

The level shift board does not need an external 24V supply — the MC508 sources
24V internally through the 6.8kΩ series resistor. The ULN2003A just sinks
that current to ground.

## Stepper Port Wirelist

Two stepper axes per ATYPE 43 port (axis N and axis N+8). Each port drives
two KL-4030 stepper drivers.

### Single-Ended Connection

The MC508 pulse/direction outputs are RS-422 differential. The KL-4030 inputs
are opto-isolated with both LED terminals accessible. We use single-ended
connection: only the + output from each RS-422 pair connects to the driver's
PUL+/DIR+, and the driver's PUL-/DIR- ties to MC508 0V (pin 15, signal ground).

This avoids reverse-biasing the opto LED (~5V reverse) when the RS-422 output
is in the low state. The complementary /Pulse and /Dir outputs are left
unconnected.

### Axis N (pins 1, 3) → KL-4030 Driver A

| MC508 MDR Pin | SCSI Wire | MC508 Signal | KL-4030 Pin | Notes              |
|---------------|-----------|--------------|-------------|--------------------|
| 1             | BLK       | Pulse(N)+    | PUL+        | Signal             |
| 15            | WHT/BRN   | 0V           | PUL-        | Ground reference   |
| 3             | RED       | Dir(N)+      | DIR+        | Signal             |
| 15            | WHT/BRN   | 0V           | DIR-        | Ground reference   |

Pins 2, 4 (/Pulse, /Dir) not connected.

### Axis N+8 (pins 11, 13) → KL-4030 Driver B

| MC508 MDR Pin | SCSI Wire | MC508 Signal   | KL-4030 Pin | Notes              |
|---------------|-----------|----------------|-------------|--------------------|
| 11            | LTGRN     | Pulse(N+8)+    | PUL+        | Signal             |
| 15            | WHT/BRN   | 0V             | PUL-        | Ground reference   |
| 13            | PINK      | Dir(N+8)+      | DIR+        | Signal             |
| 15            | WHT/BRN   | 0V             | DIR-        | Ground reference   |

Pins 12, 14 (/Pulse(N+8), /Dir(N+8)) not connected.

### Port Assignment

| MC508 Port | Axis N | Axis N+8 | Stepper Axes |
|------------|--------|----------|--------------|
| Port 0     | 0 (X)  | 8 (X')   | X + one spare or Y |
| Port 2     | 2 (Z)  | —        | Z only (if 3 axes) |

Exact axis-to-port assignment TBD based on physical layout.

## Enable and E-Stop Wiring

### Stepper Driver Enable

The KL-4030 enable input (ENA+/ENA-) is an opto-isolator. We use the MC508
WDOG SSR relay to switch the enable circuit. Per-axis AXIS_ENABLE is not used.

**Circuit (per stepper port, shared by both drivers on that port):**

```
Ext 5V+ → E-stop NC → WDOG+ (pin 7, BLU) → WDOG- (pin 8, PUR) →
  ├→ Driver A ENA+ → Driver A ENA- → Ext 5V return
  └→ Driver B ENA+ → Driver B ENA- → Ext 5V return

MC508 0V (pin 15) → Ext 5V GND  (signal ground tie)
```

- No current-limiting resistors needed — KL-4030 ENA opto inputs are designed
  for 5V direct drive (internal current limiting).
- E-stop is NC (normally closed) pushbutton in series — pressing it breaks
  the enable circuit at the hardware level regardless of MC508 software state.
- WDOG SSR rated 24V/100mA, ~25Ω on-resistance. At 5V with two optos the
  current is well within rating.
- All stepper ports share the same E-stop button (wired in series before
  splitting to each port's WDOG).
- MC508 0V (pin 15) must be tied to Ext 5V GND for a common ground reference.

### E-Stop Software Feedback (Optional)

Wire E-stop to one MC508 digital input (0-15) so software can detect the
E-stop state for status display and controlled recovery. This is not required
for safety — the hardwired circuit above handles that.

## Wiring Diagrams (WireViz)

WireViz YAML definitions for the two adapter cables:

- **`wiring_encoder.yml`** — Encoder/limits adapter (DB-25 → MC508 encoder port + level shift)
- **`wiring_stepper.yml`** — Stepper port + enable/E-stop (MC508 stepper port → 2× KL-4030 drivers)

Run `gen_wiring.bat` to regenerate diagrams (SVG + PNG + BOM).

**This document (stage_wiring.md) is the definitive wiring reference.**
The YAML files are rendering inputs for WireViz only — they should match
the wirelists here but contain no additional design rationale.

## Next Steps

1. **Build ULN2003A interface board** for limit switch level shifting (5V → 24V sink)
2. **Design/build adapter cables**
3. **Write MC_CONFIG.bas** — axis type assignments and initial configuration
