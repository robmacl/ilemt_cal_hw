' MC_CONFIG.bas — ILEMT Calibration Stage
' Runs at power-up on MC508 P849
'
' Axis assignment (one axis for initial testing):
'   Port 0: Encoder input (ATYPE 76) — axis 0
'   Port 4: Stepper output (ATYPE 43) — axis 4 (+ axis 12 for second driver)
'
' Limit switches on encoder port 0 inputs:
'   Input 16 = Pos limit (port 0 pin 9)
'   Input 17 = Neg limit (port 0 pin 20)

' Encoder input with Z index on port 0
ATYPE AXIS(0) = 76

' Stepper pulse+direction output on port 4
ATYPE AXIS(4) = 43
