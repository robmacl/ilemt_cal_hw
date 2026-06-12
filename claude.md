

## Project Overview

This project involves interfacing a precision motion stage to a Trio MC5408 P849 motion controller for the ILEMT Electromagnetic position tracker calibration system. The stage will be controlled from LabVIEW.

**Status (2026-06):** Cabling and the MIC2981 limit interface are complete on
all four axes (X, Y, Z, Rz). The MC508 power-on init and homing are written and
validated on hardware: `STARTUP.BAS` does coarse limit homing plus a fine
encoder Z-index datum (verified sub-microstep repeatable on all four axes). Set
it to power-up autorun with
`python stage/trio_upload_config.py STARTUP.BAS --no-upload --autorun`.
Remaining work is LabVIEW integration.

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
- [x] Design/build adapter cables
- [x] Build MIC2981 interface board for limit switch level shifting

### Motion Controller Configuration
- [x] Write MC_CONFIG.bas initialization file
- [x] Configure axes as ATYPE 43 (stepper) and ATYPE 76 (encoder)
- [x] Write power-on init + homing (`STARTUP.BAS`): limit homing + Z-index datum
      via REGIST (DATUM is unusable on the split-axis layout). Validated on all
      four axes; set to autorun with `trio_upload_config.py --autorun`.
- [ ] Implement custom closed-loop control algorithm (lives in LabVIEW; the
      MC508 owns init/homing/status only)

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

Detailed FlexAxis connector pin functions for ATYPE 43 (stepper) and ATYPE 76 (encoder) are in [stage/stage_wiring.md](stage/stage_wiring.md) ("MC508 Flex Axis Connector Pinout"). The per-axis limit-input map is in [stage/Configuration.md](stage/Configuration.md) ("Limit Switch Inputs").

### Homing Procedure
Implemented in `stage/STARTUP.BAS` and validated on hardware; the authoritative
description is in Configuration.md ("Homing (split-axis)"). The split-axis
constraint (why DATUM cannot be used) is that the encoder and stepper are on
different MC508 axes, so the Z index is captured on the encoder axis (via
`REGIST`) while the stepper axis moves. `stage/index_test.py` is the standalone
index-verification tool.

The homing procedure (per axis):
- Run in reverse until negative limit is hit.
- Run forward until positive limit is hit.
- Go to the +/- midpoint, then creep (fixed per-axis direction) until the
  encoder Z/index pulse and set the origin there (`OFFPOS` both axes to the
  index). The midpoint->index offset is reported per axis (`IDX_OFF` VRs); if it
  is too small, that axis's seek direction can be flipped (`seek_dir[]`). On the
  current hardware all four offsets are well-separated, so no flips are needed.

Home axes in this sequence:
- Axes 1-3 XYZ (these can be concurrent or sequential) 
- Axis 4 (z rotation)

Axis 4 is homed last because it can cause large motion of attached fixtures which might result in a collision.

Because of the need for human supervision to make sure that nothing is fouled, homing needs to be explicitly initiated using the Labview UI. Labview also needs to be able to query whether the stage has been homed since we don't want to have to home after each time the labview restarts.
### Registration Inputs (Inputs 0-7 only)
**Registration** = Hardware position capture at the instant an input triggers

**Used for:**
- Encoder Z index capture during DATUM operations (automatic)
- High-speed event position capture via REGIST command

**NOT needed for:**
- Limit switches (use any input 0-15)
- General control signals

## Repository Structure

- `claude.md` - project orientation and index (this file)
- `stage/` - motion stage interfacing work
  - `Configuration.md` - controller config: axis map, units, I/O, quirks, homing, pin functions
  - `stage_wiring.md` - physical/electrical wiring, adapter wirelist, harness diagrams
  - `MC_CONFIG.bas` - power-on axis-type (ATYPE) assignments
  - `trio_cmd.py`, `trio_upload_config.py`, `z_axis_test.py` - host-side Python tooling
  - `wiring_*.yml`, `gen_wiring.bat` - WireViz harness sources and generator
  - `Pics/` - reference photos
  - `TrioDocumentation/` - extracted Trio help (TrioBASIC, MotionPerfect)
  - `mechanical/` - sensor boom CAD
- `optical/` - optical sensor bracket and target SolidWorks designs
- `b82450a_e.pdf`, `b82451l_e.pdf`, `TC1812.pdf` - component datasheets
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

Detailed findings now live with their topic:

- **Electrical interface** (24V PNP inputs, MIC2981 level shifting, encoder
  power, Step/Dir to KL-4030, drive-enable wiring) -
  [stage/stage_wiring.md](stage/stage_wiring.md).
- **Controller design rationale and quirks** (P849 N+8 dual-axis ports, WDOG
  used as drive enable, ATYPE-after-power-cycle, split-axis homing) -
  [stage/Configuration.md](stage/Configuration.md).

## Wiring Diagram Tools

- **WireViz** (`pip install wireviz`): Generates harness diagrams from YAML. Requires **Graphviz** (`dot`).
- **Graphviz**: Install from https://graphviz.org/ — Windows installer doesn't add to PATH automatically.
- Run `stage/gen_wiring.bat` to regenerate all diagrams (handles PATH setup).

## Next Steps

1. ~~Write MC_CONFIG.bas — axis type assignments~~ (done)
2. ~~Implement homing (`STARTUP.BAS`, limit + Z-index)~~ (done, validated)
3. **LabVIEW integration** — communication library and motion control, using the
   VR interface in Configuration.md ("MC508 ↔ LabVIEW Interface"): write
   `HOME_REQ`/`CLR_FAULT`, poll `HOMED`/`BUSY`/`FAULT`/etc., and run the
   closed-loop point-to-point/creep moves around the encoder.

## Notes

- GitHub repo: https://github.com/robmacl/ilemt_cal_hw.git
- Large binary files (*.msi, *.zip) excluded from repo
- Original NI UMI-7774 cables need adaptation to MC508 flexible axis connectors
- MC508 P849 supports up to 16 axes (8 full servo/stepper + 8 pulse output)
