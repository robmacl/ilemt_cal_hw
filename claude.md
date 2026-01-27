# ILEMT Calibration Hardware Project

## Project Overview

This project involves interfacing a precision motion stage to a Trio MC5408 P849 motion controller for the ILEMT (Interferometric Laser Electron Metrology Test) calibration system. The stage will be controlled from LabVIEW.

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
  - Existing stage cables terminate for this connector

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
- [ ] Document NI UMI-7774 pinout
- [ ] Map existing stage cable connections

### Cable Adaptation (Immediate Task)
**Goal:** Create wirelist to adapt existing stage cables from NI UMI-7774 to Trio MC508

- [ ] Document existing cable pinouts from NI UMI-7774
- [ ] Map to MC508 flexible axis connectors
- [ ] Create wirelist for each axis
- [ ] Identify any needed breakout boards or adapters
- [ ] Design/specify cable assemblies

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

**Pin Assignments for ATYPE 43 (Stepper Output):**
- Pins 1-2: Pulse / /Pulse (differential)
- Pins 3-4: Direction / /Direction (differential)
- Pins 11-12: Enable / /Enable (differential)
- Pins 7-8: WDOG relay output
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
├── claude.md                 # This file
├── .gitignore               # Git ignore rules
├── optical/                 # Optical sensor designs
│   ├── X_bracket.SLDPRT
│   ├── YZ_bracket.SLDPRT
│   ├── sensor_mount.SLDASM
│   └── components/
├── stage/                   # Motion stage documentation
│   ├── MC508 Manual.pdf
│   ├── MC508 v3.0.pdf
│   ├── NI_UMI-77774pdf.pdf
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
- `WDOG` - Enables amplifier enable relay

## Next Steps

1. **Cable Documentation** (Immediate)
   - Photograph existing cable connectors
   - Document NI UMI-7774 pinout from manual
   - Create pin-to-pin mapping spreadsheet

2. **Adapter Design**
   - Determine if breakout boards needed
   - Design or specify cable assemblies
   - Create wirelist documents

3. **Initial Testing**
   - Connect one axis as proof-of-concept
   - Test encoder reading
   - Test stepper pulse output
   - Verify homing sequence

4. **Software Development**
   - Write MC_CONFIG.bas
   - Develop LabVIEW communication library
   - Implement motion control wrapper
   - Create test/calibration routines

## Notes

- GitHub repo: https://github.com/robmacl/ilemt_cal_hw.git
- Large binary files (*.msi, *.zip) excluded from repo
- Original NI UMI-7774 cables need adaptation to MC508 flexible axis connectors
- MC508 P849 supports up to 16 axes (8 full servo/stepper + 8 pulse output)
