' MC_CONFIG.bas - Trio MC508 P849 Axis Type Configuration
' Only ATYPE assignments belong here (applied at power-up).
' All other parameters are set in the startup program.
'
' Z axis: encoder on port 2, stepper on port 5 (DRV_A)
ATYPE AXIS(2) = 76
ATYPE AXIS(5) = 43
