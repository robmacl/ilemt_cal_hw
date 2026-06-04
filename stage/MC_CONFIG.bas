' MC_CONFIG.bas - Trio MC508 P849 axis-type (ATYPE) assignments
'
' Applied automatically at power-up. ATYPE changes require a FULL POWER
' CYCLE to take effect (not a software reset). Only ATYPE assignments
' belong in this file; all other parameters are set at runtime by
' STARTUP.BAS.
'
' Per stage axis: one encoder axis (ATYPE 76) + one stepper axis (ATYPE 43).
'
' *** TEMPORARY (2026-06): each stepper is on its OWN primary connector
' (one stepper per port). The P849 n+8 second-axis-per-connector output did
' not work (the primary ATYPE-43 enable claims pins 11-14), so we use four
' separate stepper ports instead. Treat as provisional until validated. ***
'
'   Axis | Name | Enc axis | Enc port | Step axis | Step port
'     0  |  X   |    0     |    0     |     4     |    4
'     1  |  Y   |    1     |    1     |     5     |    5
'     2  |  Z   |    2     |    2     |     6     |    6
'     3  |  Rz  |    3     |    3     |     7     |    7
'
ATYPE AXIS(0) = 76
ATYPE AXIS(1) = 76
ATYPE AXIS(2) = 76
ATYPE AXIS(3) = 76
ATYPE AXIS(4) = 43
ATYPE AXIS(5) = 43
ATYPE AXIS(6) = 43
ATYPE AXIS(7) = 43
