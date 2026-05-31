' MC_CONFIG.bas - Trio MC508 P849 axis-type (ATYPE) assignments
'
' Applied automatically at power-up. ATYPE changes require a FULL POWER
' CYCLE to take effect (not a software reset). Only ATYPE assignments
' belong in this file; all other parameters are set at runtime by
' STARTUP.BAS.
'
' Per stage axis: one encoder axis (ATYPE 76) + one stepper axis (ATYPE 43).
'
'   Axis | Name | Enc axis | Step axis
'     0  |  X   |    0     |     4
'     1  |  Y   |    1     |    12
'     2  |  Z   |    2     |     5
'     3  |  Rz  |    3     |    13
'
ATYPE AXIS(0) = 76
ATYPE AXIS(1) = 76
ATYPE AXIS(2) = 76
ATYPE AXIS(3) = 76
ATYPE AXIS(4) = 43
ATYPE AXIS(12) = 43
ATYPE AXIS(5) = 43
ATYPE AXIS(13) = 43
