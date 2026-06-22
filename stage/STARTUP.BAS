' STARTUP.BAS - MC508 power-on init + homing for the ILEMT cal stage
'
' Set to run at power-up (RUNTYPE STARTUP,1 - see Configuration.md).
' Assumes MC_CONFIG.bas has set ATYPE 76 (encoder) / 43 (stepper) and the
' controller has been power-cycled so those ATYPEs are live.
'
' UNITS ARE MICROSTEPS on every axis (stepper UNITS=16 makes DPOS read in
' microsteps; encoder UNITS=-1.5625 makes MPOS read in microstep-equivalents
' with the sign flipped to match stepper direction). LabVIEW does its own
' point-to-point / creep moves directly via TrioPC; this program owns init,
' homing, and the status/e-stop interface only.
'
' --------------------------------------------------------------------------
' VR INTERFACE  (LabVIEW <-> MC508; see Configuration.md "MC508<->LabVIEW")
' --------------------------------------------------------------------------
'   Command  (LabVIEW writes):
'     VR(100) HOME_REQ   axis bitmask: bit0=X bit1=Y bit2=Z bit3=Rz
'     VR(101) CLR_FAULT   write <>0 to clear FAULT/ESTOP latch
'   Status   (LabVIEW polls):
'     VR(110) HOMED      axis bitmask, persists until power cycle
'     VR(111) BUSY       1 while homing in progress
'     VR(112) ESTOP      1 if e-stop currently asserted (live input)
'     VR(113) FAULT      fault code (0=OK); see codes below
'     VR(114) FAULT_AXIS axis index (0-3) the fault occurred on
'     VR(115) STATE      coarse progress code for the live monitor
'     VR(116) CUR_AXIS   axis (0-3) currently being homed
'     VR(120..123) RANGE_STP   measured stepper travel per axis (microsteps)
'     VR(124..127) RANGE_ENC   measured encoder travel per axis (microsteps)
'     VR(128..131) IDX_OFF     midpoint->index offset per axis (microsteps);
'                              flag if |IDX_OFF| < IDX_MIN (consider flipping
'                              that axis's seek_dir)
'   Detail string:
'     VR(200..249) packed ASCII, read with  PRINT VRSTRING(200)
'
'   FAULT codes:  0 OK  1 NEG_LIMIT_NOT_FOUND  2 POS_LIMIT_NOT_FOUND
'                 4 RANGE_TOO_SMALL  6 ESTOP_ABORT  7 TIMEOUT
'                 8 STALL (demand outran encoder; likely a missing/dead limit)
'                 9 INDEX_NOT_FOUND (no encoder Z mark within IDX_SWEEP)
'   STATE codes:  0 idle  1 init_done  10 seek_neg  11 seek_pos
'                12 to_mid  13 axis_homed  14 seek_index  90 fault  91 estop_abort
' --------------------------------------------------------------------------

' Arrays must be declared "AS type(size)"; size N gives indices 0..N-1.
DIM step_ax AS INTEGER(4)
DIM enc_ax AS INTEGER(4)
DIM fwd_inp AS INTEGER(4)
DIM rev_inp AS INTEGER(4)
DIM maskv AS INTEGER(4)
DIM enc_sign AS FLOAT(4)
DIM rng_stp AS FLOAT(4)
DIM rng_enc AS FLOAT(4)
DIM seek_dir AS INTEGER(4)
DIM idx_off AS FLOAT(4)
DIM msg AS STRING(50)
' Scalars (ax, sa, ea, seek_sign, sn, sp, en, ep, midp, t, ok, mi, msglen)
' are left undeclared: local variables default to FLOAT.

' ---- Per-axis hardware map (see Configuration.md) ----
' Index = stage axis (0=X 1=Y 2=Z 3=Rz).
' One stepper per port: X=4 Y=5 Z=6 Rz=7 (the n+8 second-axis output on
' ports 4/5 did not work, so each stepper uses its own primary connector).
' Limit inputs are unchanged (they ride on the encoder ports 0-3).
step_ax(0) = 4
step_ax(1) = 5
step_ax(2) = 6
step_ax(3) = 7
enc_ax(0) = 0
enc_ax(1) = 1
enc_ax(2) = 2
enc_ax(3) = 3
fwd_inp(0) = 16
fwd_inp(1) = 18
fwd_inp(2) = 20
fwd_inp(3) = 23
rev_inp(0) = 17
rev_inp(1) = 19
rev_inp(2) = 21
rev_inp(3) = 22
maskv(0) = 1
maskv(1) = 2
maskv(2) = 4
maskv(3) = 8

' Per-axis encoder sign (cabling is non-uniform). -1 = encoder counts same
' direction as stepper demand (X/Y/Z); +1 = inverted differential pair so the
' encoder counts opposite (Rz). enc UNITS = enc_sign * 1.5625.
' Rz (3): limits also swapped above (fwd=23 rev=22) vs the wired-default 22/23,
' because the actuator tab reaches the sensors opposite to the seek direction.
enc_sign(0) = -1
enc_sign(1) = -1
enc_sign(2) = -1
enc_sign(3) = 1

' Per-axis index seek direction from the midpoint: +1 = seek the Z index in the
' + direction, -1 = in the - direction. Fixed per axis so homing always
' converges on the same index. After a homing run, check IDX_OFF (VR 128..131):
' if an axis's |midpoint->index| is small (< IDX_MIN), flip that axis to -1 here
' so it catches the well-separated index on the other side instead.
seek_dir(0) = 1
seek_dir(1) = 1
seek_dir(2) = 1
seek_dir(3) = 1

' ---- Tunable parameters (microstep units) ----
' Scalars are left undeclared (local variables default to FLOAT); DIM cannot
' take a comma-separated list, only "DIM name AS type".
STEP_UNITS = 16          ' DPOS in microsteps (x16 FlexAxis multiplier)
ENC_UNITS_MAG = 1.5625   ' |enc UNITS| = 10000 enc / 6400 ustep; sign per axis (enc_sign)
RUN_SPEED = 18900        ' ~15 mm/s (XYZ) / ~5.9 deg/s (Rz); same RPM
RUN_ACCEL = 63000        ' ~50 mm/s^2 equivalent
HOME_SPEED = 6300        ' ~5 mm/s slow approach to limits
HOME_DIST = 2000000      ' "drive until limit stops us" distance, usteps
MIN_RANGE = 5000         ' self-test floor: travel must exceed this
HOME_TMO = 6000          ' seek timeout in 20ms ticks (~120 s) - generous backstop
STALL_THRESH = 400       ' stall: |stepper demand - encoder| divergence, usteps
IDX_SWEEP = 8000         ' index seek distance, usteps (>1 motor rev = 6400)
IDX_MIN = 1280           ' report-only flag: |midpoint->index| < this (~0.2 rev)
ESTOP_IN = 0             ' input XA0 (expansion A term 0): ON=released, OFF=pressed
MSG_BASE = 200

' ==========================================================================
' INIT (runs once at power-up)
' ==========================================================================
RAPIDSTOP(2)
WA(50)
RAPIDSTOP(2)

FOR ax = 0 TO 3
  sa = step_ax(ax)
  ea = enc_ax(ax)

  ' Stepper axis: open loop, microstep units, limits assigned here.
  BASE(sa)
  SERVO = OFF
  UNITS = STEP_UNITS
  SPEED = RUN_SPEED
  ACCEL = RUN_ACCEL
  DECEL = RUN_ACCEL
  ' FASTDEC: abrupt stop on limit / CANCEL / RAPIDSTOP only (normal moves use
  ' DECEL). A limit hit after homing is a fault, so stop hard to stay off the
  ' hard stop. Overshoot ~= RUN_SPEED^2 / (2 * FASTDEC).
  FASTDEC = RUN_ACCEL * 40
  CREEP = HOME_SPEED
  FWD_IN = fwd_inp(ax)
  REV_IN = rev_inp(ax)
  INVERT_IN(fwd_inp(ax), OFF)
  INVERT_IN(rev_inp(ax), OFF)

  ' Encoder axis: read-only feedback. Do NOT set SPEED/ACCEL/CREEP here -
  ' negative UNITS makes those error out (see Configuration.md quirk).
  BASE(ea)
  SERVO = OFF
  UNITS = enc_sign(ax) * ENC_UNITS_MAG
  ' DATUM_IN is unused: Z-index homing uses REGIST on this axis (see
  ' do_home_axis step 4), and the limits are enforced via FWD_IN/REV_IN on the
  ' stepper axis. Left set (harmless) only as a record of the limit-input map.
  DATUM_IN = rev_inp(ax)
NEXT ax

WDOG = ON                        ' energize drive-enable relay

VR(110) = 0                      ' HOMED  (cleared on power-up)
VR(111) = 0                      ' BUSY
VR(113) = 0                      ' FAULT
VR(114) = -1                     ' FAULT_AXIS
VR(115) = 1                      ' STATE = init_done
VR(116) = -1                     ' CUR_AXIS
msg = "Init complete. Awaiting HOME_REQ."
GOSUB store_msg

' ==========================================================================
' MAIN LOOP
' ==========================================================================
WHILE TRUE
  ' Live e-stop status for LabVIEW.
  ' ESTOP_IN reads ON when e-stop is released (out), OFF when pressed.
  IF IN(ESTOP_IN) = OFF THEN
    VR(112) = 1                  ' e-stop asserted (pressed)
  ELSE
    VR(112) = 0
  ENDIF

  ' Fault/e-stop latch clear request.
  IF VR(101) <> 0 THEN
    VR(101) = 0
    VR(113) = 0
    VR(114) = -1
    IF VR(115) >= 90 THEN VR(115) = 0
    msg = "Fault cleared."
    GOSUB store_msg
  ENDIF

  ' Home request: process requested axes in order 0,1,2,3 (Rz=bit3 last).
  ' A fresh request auto-clears a stale fault latch (as long as e-stop is
  ' released), so re-pressing Home after a fault just retries.
  IF (VR(100) <> 0) AND (VR(112) = 0) THEN
    IF VR(113) <> 0 THEN
      VR(113) = 0
      VR(114) = -1
      IF VR(115) >= 90 THEN VR(115) = 0
    ENDIF
    GOSUB do_home_all
    VR(100) = 0
  ENDIF

  WA(50)
WEND

' ==========================================================================
' HOME ALL REQUESTED AXES
' ==========================================================================
do_home_all:
  VR(111) = 1                    ' BUSY
  FOR ax = 0 TO 3
    IF (VR(100) AND maskv(ax)) <> 0 THEN
      GOSUB do_home_axis
      IF VR(113) <> 0 THEN
        VR(111) = 0
        RETURN                   ' abort remaining axes on any fault
      ENDIF
    ENDIF
  NEXT ax
  VR(111) = 0
  VR(115) = 0                    ' back to idle
  msg = "Homing complete."
  GOSUB store_msg
  RETURN

' ==========================================================================
' HOME ONE AXIS  (uses ax; sets sa, ea)
'   1. seek negative limit, record positions
'   2. seek positive limit, record positions  (both-limits self test)
'   3. move to geometric midpoint, zero both axes there
'   4. seek the encoder Z index (fixed dir) and make the index the datum
' ==========================================================================
do_home_axis:
  sa = step_ax(ax)
  ea = enc_ax(ax)
  VR(116) = ax
  VR(110) = VR(110) AND (255 - maskv(ax))    ' clear HOMED bit while re-homing

  BASE(sa)
  SPEED = HOME_SPEED

  ' ---- 1. seek negative limit ----
  VR(115) = 10
  msg = "Axis " + STR(ax, 0) + ": seeking neg limit"
  GOSUB store_msg
  seek_sign = -1
  GOSUB do_seek
  IF ok = 0 THEN
    GOSUB chk_abort_cause
    VR(114) = ax
    IF VR(113) = 0 THEN VR(113) = 1        ' NEG_LIMIT_NOT_FOUND
    GOSUB report_fault
    RETURN
  ENDIF
  IF IN(rev_inp(ax)) <> 0 THEN             ' expect 0 (at limit)
    VR(113) = 1
    VR(114) = ax
    GOSUB report_fault
    RETURN
  ENDIF
  sn = DPOS AXIS(sa)
  en = MPOS AXIS(ea)

  ' ---- 2. seek positive limit ----
  VR(115) = 11
  msg = "Axis " + STR(ax, 0) + ": seeking pos limit"
  GOSUB store_msg
  seek_sign = 1
  GOSUB do_seek
  IF ok = 0 THEN
    GOSUB chk_abort_cause
    VR(114) = ax
    IF VR(113) = 0 THEN VR(113) = 2        ' POS_LIMIT_NOT_FOUND
    GOSUB report_fault
    RETURN
  ENDIF
  IF IN(fwd_inp(ax)) <> 0 THEN
    VR(113) = 2
    VR(114) = ax
    GOSUB report_fault
    RETURN
  ENDIF
  sp = DPOS AXIS(sa)
  ep = MPOS AXIS(ea)

  ' ---- range / self test ----
  rng_stp(ax) = sp - sn
  rng_enc(ax) = ep - en
  VR(120 + ax) = rng_stp(ax)
  VR(124 + ax) = rng_enc(ax)
  IF ABS(rng_stp(ax)) < MIN_RANGE THEN
    VR(113) = 4                            ' RANGE_TOO_SMALL
    VR(114) = ax
    GOSUB report_fault
    RETURN
  ENDIF

  ' ---- 3. move to midpoint and zero both axes ----
  VR(115) = 12
  msg = "Axis " + STR(ax, 0) + ": to midpoint"
  GOSUB store_msg
  midp = (sn + sp) / 2
  BASE(sa)
  MOVEABS(midp)
  GOSUB wait_move
  IF ok = 0 THEN
    GOSUB chk_abort_cause
    VR(114) = ax
    GOSUB report_fault
    RETURN
  ENDIF

  ' Zero at the midpoint so REG_POS reads directly as the midpoint->index
  ' distance, and so the index seek starts from a repeatable point.
  DEFPOS(0) AXIS(sa)
  DEFPOS(0) AXIS(ea)

  ' ---- 4. seek the encoder Z index, make it the datum ----
  VR(115) = 14
  msg = "Axis " + STR(ax, 0) + ": seeking index"
  GOSUB store_msg

  BASE(ea)
  REGIST(20, 0, 1, 0, 0)                   ' arm channel A on the encoder Z mark
  BASE(sa)
  IF seek_dir(ax) < 0 THEN
    MOVE(-IDX_SWEEP)
  ELSE
    MOVE(IDX_SWEEP)
  ENDIF
  GOSUB wait_mark                          ' sets ok, and idx = REG_POS at index
  IF ok = 0 THEN
    GOSUB chk_abort_cause
    VR(114) = ax
    GOSUB report_fault
    RETURN
  ENDIF

  ' idx = encoder position at the index, relative to the midpoint = the
  ' midpoint->index offset (signed). Record it, then shift both axes so the
  ' index reads 0. The encoder is the datum; the stepper tracks 1:1 in
  ' microsteps, so the same offset keeps DPOS aligned with the encoder. We do
  ' NOT move back to the index (REG_POS is hardware-latched and exact, so the
  ' math datum is as repeatable as the index itself).
  idx_off(ax) = idx
  VR(128 + ax) = idx
  OFFPOS AXIS(ea) = -idx
  OFFPOS AXIS(sa) = -idx
  WA(20)

  BASE(sa)
  SPEED = RUN_SPEED                        ' restore (seek phases used HOME_SPEED)

  VR(110) = VR(110) OR maskv(ax)           ' set HOMED bit
  VR(115) = 13
  IF ABS(idx) < IDX_MIN THEN
    msg = "Axis " + STR(ax, 0) + " homed. idx=" + STR(idx, 0) + " (SMALL-consider flip)"
  ELSE
    msg = "Axis " + STR(ax, 0) + " homed. idx=" + STR(idx, 0)
  ENDIF
  GOSUB store_msg
  RETURN

' ==========================================================================
' SEEK toward a limit:  drive HOME_DIST in seek_sign direction; the limit
' input cancels the move.  Sets ok=1 if motion stopped normally, ok=0 on
' e-stop or timeout.  Uses sa, seek_sign.
' ==========================================================================
do_seek:
  BASE(sa)
  IF seek_sign < 0 THEN
    MOVE(-HOME_DIST)
  ELSE
    MOVE(HOME_DIST)
  ENDIF
  GOSUB wait_move
  RETURN

' Wait for the current move on sa to finish, watching e-stop, stall, timeout.
' Stall = stepper demand (DPOS) and shaft encoder (MPOS) diverge: the motor is
' commanded but isn't following (hardstop, dead limit, collision). The encoder
' is on the motor shaft, so a true stall shows up here within ~1 tick.
' Sets abort_reason: 0 none, 1 e-stop, 2 stall, 3 timeout.
wait_move:
  ok = 1
  abort_reason = 0
  t = 0
  sd0 = DPOS AXIS(sa)
  se0 = MPOS AXIS(ea)
  REPEAT
    WA(20)
    t = t + 1
    IF IN(ESTOP_IN) = OFF THEN              ' e-stop pressed -> abort
      ok = 0
      abort_reason = 1
    ENDIF
    dd = (DPOS AXIS(sa) - sd0) - (MPOS AXIS(ea) - se0)
    IF ABS(dd) > STALL_THRESH THEN          ' demand outran the shaft
      ok = 0
      abort_reason = 2
    ENDIF
    IF t > HOME_TMO THEN
      ok = 0
      abort_reason = 3
    ENDIF
  UNTIL (MTYPE AXIS(sa) = 0) OR (ok = 0)
  IF ok = 0 THEN CANCEL AXIS(sa)
  RETURN

' Creep sa toward the index while a Z-mark REGIST is armed on ea. On the mark,
' capture idx = REG_POS (hardware-latched at the index, so poll latency and any
' overshoot do not affect it) and stop. Sets ok=1 on capture; ok=0 with
' abort_reason on e-stop(1)/stall(2)/timeout(3)/no-index(4). Same guards as
' wait_move; "no-index" means the sweep finished without ever seeing the mark.
wait_mark:
  ok = 0
  abort_reason = 0
  t = 0
  sd0 = DPOS AXIS(sa)
  se0 = MPOS AXIS(ea)
  REPEAT
    WA(20)
    t = t + 1
    IF MARK AXIS(ea) THEN
      idx = REG_POS AXIS(ea)
      ok = 1
    ELSEIF IN(ESTOP_IN) = OFF THEN
      abort_reason = 1
    ELSE
      dd = (DPOS AXIS(sa) - sd0) - (MPOS AXIS(ea) - se0)
      IF ABS(dd) > STALL_THRESH THEN
        abort_reason = 2
      ELSEIF t > HOME_TMO THEN
        abort_reason = 3
      ENDIF
    ENDIF
  UNTIL (ok = 1) OR (abort_reason <> 0) OR (MTYPE AXIS(sa) = 0)
  IF (ok = 0) AND (abort_reason = 0) THEN abort_reason = 4   ' moved, no mark
  CANCEL AXIS(sa)
  RETURN

' Map abort_reason (set by wait_move / wait_mark) to a fault code.
chk_abort_cause:
  IF abort_reason = 1 THEN
    VR(113) = 6                            ' ESTOP_ABORT
    VR(115) = 91
  ELSEIF abort_reason = 2 THEN
    VR(113) = 8                            ' STALL (likely a missing/dead limit)
    VR(115) = 90
  ELSEIF abort_reason = 4 THEN
    VR(113) = 9                            ' INDEX_NOT_FOUND
    VR(115) = 90
  ELSE
    VR(113) = 7                            ' TIMEOUT
    VR(115) = 90
  ENDIF
  RETURN

report_fault:
  IF VR(115) < 90 THEN VR(115) = 90
  VR(110) = VR(110) AND (255 - maskv(ax))  ' this axis is not homed
  RAPIDSTOP(2)
  msg = "FAULT " + STR(VR(113), 0) + " on axis " + STR(ax, 0)
  GOSUB store_msg
  RETURN

' Pack 'msg' into VR(MSG_BASE..) as null-terminated ASCII for VRSTRING.
store_msg:
  msglen = LEN(msg)
  FOR mi = 0 TO msglen - 1
    VR(MSG_BASE + mi) = ASC(msg, mi)
  NEXT mi
  VR(MSG_BASE + msglen) = 0
  RETURN
