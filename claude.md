# ILEMT Calibration Hardware Project

## Project Overview

This project involves interfacing a precision motion stage to a Trio MC5408 P849 motion controller for the ILEMT Electromagnetic position tracker calibration system. The stage will be controlled from LabVIEW.

## Hardware Components

### Motion Controller
- **Trio MC5408 P849** - 8-axis motion coordinator
  - P849 version: 8 servo/stepper axes + 8 additional pulse output axes
  - ARM Cortex-A9 processor
  - 10/100 Base-T Ethernet
  - 32 digital inputs (16 built-in, expandable)
  - 16 digital outputs
  - Documentation: `stage/MC508 Manual.pdf`, `stage/MC508 v3.0.pdf`
  - Extracted help files: `stage/TrioDocumentation/`

### Previous Setup
- **NI UMI-7774** - National Instruments breakout interface
  - Documentation: `stage/NI_UMI-77774pdf.pdf`
  - Existing stage cables terminate for this connector (DB-25 male)

### Stepper Drivers
- **KL-4030** (Keling) - Stepper motor drivers
  - Opto-isolated inputs for PUL+/-, DIR+/-, ENA+/-
  - Two drivers per MC508 stepper port (axis N and N+8)

### Motion Stage
- Precision XYZ stage with stepper motors and encoders
- Each axis has:
  - Stepper motor for positioning
  - Encoder with index pulse for feedback
  - Limit switches for homing

### Optical Sensors
- SolidWorks designs in `optical/`
- Mounting brackets and target designs

## Current Project Scope

### Understanding Phase
- [x] Review Trio MC508 documentation
- [x] Understand flexible axis pin configuration
- [x] Learn ATYPE configuration for stepper+encoder setup
- [x] Understand registration inputs vs. regular inputs
- [x] Document NI UMI-7774 pinout
- [x] Map existing stage cable connections

### Cable Adaptation
**Goal:** Create wirelist to adapt existing stage cables from NI UMI-7774 to Trio MC508

- [x] Document existing cable pinouts from NI UMI-7774
- [x] Map to MC508 flexible axis connectors
- [x] Create wirelist for each axis (encoder + stepper)
- [x] Identify needed breakout boards or adapters (MIC2981 high-side driver for limits)
- [ ] Design/build adapter cables
- [ ] Build MIC2981 interface board for limit switch level shifting

### Motion Controller Configuration
- [ ] Write MC_CONFIG.bas initialization file
- [ ] Configure axes as ATYPE 43 (stepper) and ATYPE 76 (encoder)
- [ ] Set up homing sequences using DATUM commands
- [ ] Implement custom closed-loop control algorithm

### LabVIEW Integration
- [ ] Research Trio communication protocols (Ethernet, Telnet, Modbus TCP)
- [ ] Design LabVIEW interface architecture
- [ ] Implement motion control commands
- [ ] Create position monitoring and feedback

## Technical Notes

### MC508 Flexible Axis Configuration

**Key Insight:** Pin functions are determined by ATYPE parameter set in MC_CONFIG.bas, not by runtime mode switching.

#### Stepper + Encoder Strategy
For closed-loop stepper control with encoder feedback:

**Option 1: Two Axis Ports (Recommended)**
- Axis N (e.g., 0): ATYPE 43 - Pulse+Direction output with enable
- Axis M (e.g., 1): ATYPE 76 - Encoder input with Z index

This allows:
- Full quadrature encoder feedback (A, B, Z)
- Precise homing using limit switch + Z index
- Custom control loop in user code

**Pin Assignments for ATYPE 43 (Stepper Output) — P849 variant:**
- Pins 1-2: Pulse(N) / /Pulse(N) (differential)
- Pins 3-4: Dir(N) / /Dir(N) (differential)
- Pins 11-14: Pulse(N+8) / Dir(N+8) — second stepper axis (replaces enable)
- Pins 7-8: WDOG SSR relay output (24V/100mA, ~25Ω)
- Pin 5: +5V encoder power (100mA max per port)

**Pin Assignments for ATYPE 76 (Encoder Input):**
- Pins 1-2: Encoder A / /A
- Pins 3-4: Encoder B / /B
- Pins 11-12: Encoder Z / /Z (index pulse)
- Pins 9, 20: Additional digital inputs (16+n*2, 17+n*2)

### Homing Procedure
```basic
' Example homing with limit switch + encoder index
BASE(1)  ' Encoder axis
DATUM_IN = 10  ' Any input (doesn't require registration)
SPEED = 5000   ' Fast search
CREEP = 500    ' Slow creep
DATUM(6)       ' Reverse to limit, forward to Z mark
WAIT IDLE
MPOS(0) = MPOS(1)  ' Sync stepper axis
```

### Registration Inputs (Inputs 0-7 only)
**Registration** = Hardware position capture at the instant an input triggers

**Used for:**
- Encoder Z index capture during DATUM operations (automatic)
- High-speed event position capture via REGIST command

**NOT needed for:**
- Limit switches (use any input 0-15)
- General control signals

## Repository Structure

```
ilemt_cal_hw/
├── CLAUDE.md                # This file
├── .gitignore               # Git ignore rules
├── optical/                 # Optical sensor designs
│   ├── X_bracket.SLDPRT
│   ├── YZ_bracket.SLDPRT
│   ├── sensor_mount.SLDASM
│   └── components/
├── stage/                   # Motion stage documentation & wiring
│   ├── MC508 Manual.pdf
│   ├── MC508 v3.0.pdf
│   ├── NI_UMI-77774pdf.pdf
│   ├── stage_wiring.md      # Main wiring documentation
│   ├── wiring_encoder.yml   # WireViz: encoder/limits adapter
│   ├── wiring_stepper.yml   # WireViz: stepper port + enable/E-stop
│   ├── gen_wiring.bat       # Runs WireViz on all YAML files
│   ├── Pics/
│   └── TrioDocumentation/   # Extracted help files
│       ├── MotionPerfect/
│       └── TrioBASIC/
├── b82450a_e.pdf           # Component datasheet
├── b82451l_e.pdf           # Component datasheet
└── TC1812.pdf              # Component datasheet
```

## Communication Protocols

The MC508 supports multiple protocols for LabVIEW integration:
- **Ethernet** (primary): 10/100 Base-T
- **Telnet** (Client and Server)
- **Modbus TCP** (Client and Server)
- **Ethernet/IP** (Server)
- **Trio Unified API**
- **RS232/RS485** (115200 baud max)

## References

### Key Documentation Files
- `stage/MC508 Manual.pdf` - Hardware manual, pinouts, specifications
- `stage/TrioDocumentation/TrioBASIC/ATYPE.html` - Axis type configuration
- `stage/TrioDocumentation/TrioBASIC/DATUM.html` - Homing sequences
- `stage/TrioDocumentation/TrioBASIC/REGIST.html` - Registration (position capture)

### Critical Parameters
- `ATYPE` - Sets axis hardware configuration (must be in MC_CONFIG.bas)
- `DATUM_IN` - Assigns input for homing limit switch
- `REGIST()` - Arms hardware position capture
- `SERVO` - Enables/disables servo loop (OFF for open-loop stepper)
- `WDOG` - Enables amplifier enable relay / SSR for drive enable

### Key Hardware Findings
- **MC508 inputs are ALL 24V PNP** (6.8kΩ series, opto-isolated). 5V signals need MIC2981 high-side driver.
  - MIC2981 sources 24V to input pin; current flows through internal opto + 6.8kΩ to Input Com.
  - MIC2981 Vs = +24V (same supply as MC508), MIC2981 GND = 0V.
  - MC508 Input Com (pin 10) connects to 24V 0V return.
- **MC508 VOUT+/VOUT-** are analog servo outputs (±10V DAC), NOT 24V power supply.
- **P849 dual-axis ports**: ATYPE 43 pins 11-14 carry axis N+8 (second stepper), replacing enable outputs.
- **WDOG relay** is used for drive enable instead of per-axis AXIS_ENABLE (which needs dedicated pins lost to N+8).
- **Home switch not used** — only 2 limit inputs needed per axis, matching ATYPE 76's 2 inputs.
- **Encoder power from MC508** (+5V, pin 5) avoids CM noise. Limit switches use external 5V supply.
- **Step/Dir to KL-4030**: Single-ended connection — only use + output from RS-422 pair, tie driver PUL-/DIR- to MC508 0V (pin 15). Avoids reverse-biasing opto LED when output is low.
- **KL-4030 ENA inputs**: Designed for 5V direct drive, no external current-limiting resistor needed.

## Wiring Diagram Tools

- **WireViz** (`pip install wireviz`): Generates harness diagrams from YAML. Requires **Graphviz** (`dot`).
- **Graphviz**: Install from https://graphviz.org/ — Windows installer doesn't add to PATH automatically.
- Run `stage/gen_wiring.bat` to regenerate all diagrams (handles PATH setup).

## Next Steps

1. **Build MIC2981 interface board** for limit switch level shifting (5V → 24V high-side drive)
2. **Design/build adapter cables** (DB-25 to MC508 20-pin MDR)
3. **Write MC_CONFIG.bas** — axis type assignments and initial configuration
4. **Initial testing** — one axis proof-of-concept
5. **LabVIEW integration** — communication library and motion control

## Notes

- GitHub repo: https://github.com/robmacl/ilemt_cal_hw.git
- Large binary files (*.msi, *.zip) excluded from repo
- Original NI UMI-7774 cables need adaptation to MC508 flexible axis connectors
- MC508 P849 supports up to 16 axes (8 full servo/stepper + 8 pulse output)
