"""Encoder Z-index (registration) verification for the ILEMT cal stage.

Proves, on real hardware, that each axis's encoder index channel produces a
registration MARK and that the captured REG_POS is repeatable. This is the
prerequisite for adding Z-index homing to STARTUP.BAS -- the index inputs have
never been exercised, so nothing downstream should be built until this passes.

What it does, per axis:
  Phase A (existence + spacing): creep the stepper FORWARD and capture several
    consecutive Z marks on the encoder axis. Proves the index fires and that
    consecutive indices are ~one motor rev (6400 microsteps) apart.
  Phase B (repeatability): approach ONE index from the same side, FORWARD, a
    number of times and report the REG_POS scatter. This is the number that
    matters for using the index as a home datum.

Mechanism (see TrioDocumentation/TrioBASIC/REGIST.html, Mode 20 / Example 3):
  REGIST(20, 0, 1, 0, 0) arms channel A on the Z mark (source=1), rising edge,
  no window, on the ENCODER axis. Motion is commanded on the STEPPER axis; the
  encoder rides the same shaft, so its MPOS advances and the Z mark fires as it
  crosses the index. REG_POS latches the encoder count in HARDWARE at the index,
  so telnet polling latency and decel overshoot do not affect the captured value.

Safety: prompts before every move. FWD_IN/REV_IN limits are assigned so a sweep
is cancelled at a limit. A stall check aborts if stepper demand outruns the
shaft encoder. Position the axis roughly mid-travel (clear of the + limit by a
couple of motor revs) before running.

Prerequisites:
  - MC_CONFIG.bas uploaded and controller power-cycled (ATYPE 76 enc / 43 step).
  - Drives can be energized (E-stop releasable). Coexists with STARTUP.BAS
    running -- this script never writes HOME_REQ.

Usage:
    python stage/index_test.py            # Z axis (2)
    python stage/index_test.py 2          # Z axis explicitly
    python stage/index_test.py 0 1 2 3    # all four, sequentially (prompts each)
    python stage/index_test.py 2 --reps 8
"""
import sys
import time
from trio_cmd import connect, send_cmd

# ---- Per-axis hardware map (mirrors STARTUP.BAS / Configuration.md) ----
# index = stage axis (0=X 1=Y 2=Z 3=Rz)
STEP_AX  = [4, 5, 6, 7]
ENC_AX   = [0, 1, 2, 3]
FWD_INP  = [16, 18, 20, 23]
REV_INP  = [17, 19, 21, 22]
ENC_SIGN = [-1, -1, -1, 1]      # enc UNITS = ENC_SIGN * 1.5625
AXIS_NAME = ["X", "Y", "Z", "Rz"]

# ---- Units / motion (microsteps; same as STARTUP.BAS) ----
STEP_UNITS    = 16
ENC_UNITS_MAG = 1.5625
RUN_SPEED     = 18900
HOME_SPEED    = 6300            # slow creep for index seek
RUN_ACCEL     = 63000
ONE_REV       = 6400            # microsteps/rev = index spacing
SWEEP         = 7500            # >1 rev: guarantees crossing >=1 index
BACKOFF       = 3200            # 0.5 rev: re-approach same index from same side
STALL_THRESH  = 400            # |demand - encoder| divergence abort, microsteps
ESTOP_IN      = 0              # ON=released, OFF=pressed
SETTLE        = 0.15           # s, let motion settle before reading positions


def cmd(sock, command, label=None):
    """Send a command, echo it and the response."""
    if label:
        print(f"\n--- {label} ---")
    print(f"  >> {command}")
    result = send_cmd(sock, command)
    if result:
        print(f"  {result}")
    return result


def q(sock, query):
    """Send a query, return the raw response text (no echo)."""
    return send_cmd(sock, query)


def as_float(text):
    """First whitespace token of a response as float, or None."""
    try:
        return float(text.strip().split()[0])
    except (ValueError, AttributeError, IndexError):
        return None


def qf(sock, query):
    return as_float(send_cmd(sock, query))


def is_true(sock, query):
    """Trio booleans (MARK, IDLE, ...) read back as -1 for TRUE, 0 for FALSE.
    Treat any nonzero as true. (IN() inputs are 1/0, not -1 -- don't use this
    for those.)"""
    v = qf(sock, query)
    return v is not None and abs(v) >= 0.5


def prompt(msg):
    try:
        input(f"\n>>> {msg} [Enter to continue, Ctrl-C to abort] ")
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)


def wait_idle(sock, axis, timeout=20):
    for _ in range(int(timeout / 0.1)):
        if is_true(sock, f'?IDLE AXIS({axis})'):
            return True
        time.sleep(0.1)
    print(f"  WARNING: axis {axis} not idle within {timeout}s")
    return False


def estop_pressed(sock):
    return (qf(sock, f'?IN({ESTOP_IN})') or 0) < 0.5


def configure_axis(sock, ax):
    """Idempotent setup (matches STARTUP.BAS). Safe to run alongside STARTUP."""
    sa, ea = STEP_AX[ax], ENC_AX[ax]

    atype_e = q(sock, f'?ATYPE AXIS({ea})')
    atype_s = q(sock, f'?ATYPE AXIS({sa})')
    print(f"  Encoder axis {ea} ATYPE: {atype_e}  (expect 76)")
    print(f"  Stepper axis {sa} ATYPE: {atype_s}  (expect 43)")
    if '76' not in str(atype_e) or '43' not in str(atype_s):
        print("  WARNING: ATYPE mismatch -- upload MC_CONFIG.bas and power cycle.")
        prompt("Continue anyway?")

    # Stepper axis: open loop, microstep units, limits.
    cmd(sock, f'SERVO AXIS({sa}) = OFF')
    cmd(sock, f'UNITS AXIS({sa}) = {STEP_UNITS}')
    cmd(sock, f'SPEED AXIS({sa}) = {HOME_SPEED}')
    cmd(sock, f'ACCEL AXIS({sa}) = {RUN_ACCEL}')
    cmd(sock, f'DECEL AXIS({sa}) = {RUN_ACCEL}')
    cmd(sock, f'FWD_IN AXIS({sa}) = {FWD_INP[ax]}')
    cmd(sock, f'REV_IN AXIS({sa}) = {REV_INP[ax]}')
    cmd(sock, f'INVERT_IN({FWD_INP[ax]}, OFF)')
    cmd(sock, f'INVERT_IN({REV_INP[ax]}, OFF)')

    # Encoder axis: read-only feedback. Do NOT set SPEED/ACCEL with negative
    # UNITS (errors out -- see Configuration.md quirk).
    cmd(sock, f'SERVO AXIS({ea}) = OFF')
    cmd(sock, f'UNITS AXIS({ea}) = {ENC_SIGN[ax] * ENC_UNITS_MAG}')


def seek_index(sock, ax, sweep=SWEEP):
    """Arm Z-mark registration on the encoder axis, creep the stepper FORWARD up
    to `sweep` microsteps, and capture the first index.

    Returns (reg_pos, ok). ok is False on no-index / e-stop / stall / timeout;
    reg_pos is the latched encoder position at the index (None if not found).
    """
    sa, ea = STEP_AX[ax], ENC_AX[ax]

    # Arm channel A on the Z mark (re-issued each capture, per REGIST docs).
    cmd(sock, f'BASE({ea})')
    cmd(sock, 'REGIST(20, 0, 1, 0, 0)')
    if is_true(sock, f'?MARK AXIS({ea})'):
        print("  NOTE: MARK already set after arming; re-arming.")
        send_cmd(sock, 'REGIST(20, 0, 1, 0, 0)')

    sd0 = qf(sock, f'?DPOS AXIS({sa})')
    se0 = qf(sock, f'?MPOS AXIS({ea})')

    cmd(sock, f'MOVE({sweep}) AXIS({sa})')

    reg_pos, ok = None, False
    deadline = time.time() + (sweep / HOME_SPEED) + 5.0
    while True:
        if is_true(sock, f'?MARK AXIS({ea})'):
            reg_pos = qf(sock, f'?REG_POS AXIS({ea})')
            send_cmd(sock, f'CANCEL AXIS({sa})')
            ok = True
            break
        if estop_pressed(sock):
            print("  ABORT: e-stop pressed.")
            send_cmd(sock, f'CANCEL AXIS({sa})')
            break
        # Stall: stepper demand advanced but the shaft encoder did not follow.
        dd = qf(sock, f'?DPOS AXIS({sa})')
        de = qf(sock, f'?MPOS AXIS({ea})')
        if None not in (dd, de, sd0, se0):
            if abs((dd - sd0) - (de - se0)) > STALL_THRESH:
                print("  ABORT: stall (demand outran shaft encoder).")
                send_cmd(sock, f'CANCEL AXIS({sa})')
                break
        if is_true(sock, f'?IDLE AXIS({sa})'):
            break  # sweep finished without a mark
        if time.time() > deadline:
            print("  ABORT: timeout.")
            send_cmd(sock, f'CANCEL AXIS({sa})')
            break
        time.sleep(0.04)

    wait_idle(sock, sa)
    return reg_pos, ok


def phase_a(sock, ax, count=3):
    """Catch `count` consecutive forward indices; report spacing."""
    print("\n" + "=" * 60)
    print(f"PHASE A: existence + spacing ({count} consecutive indices)")
    print("=" * 60)
    positions = []
    for i in range(count):
        reg_pos, ok = seek_index(sock, ax)
        if not ok:
            print(f"  Index {i+1}: NOT FOUND over {SWEEP} microsteps "
                  f"(>{SWEEP/ONE_REV:.2f} rev).")
            print("  -> Z channel appears dead/unwired on this axis, or the")
            print("     stage is at the + limit. Check wiring before relying on it.")
            return False
        spacing = ""
        if positions:
            spacing = f"   spacing from previous: {reg_pos - positions[-1]:+.1f}"
        print(f"  Index {i+1}: REG_POS = {reg_pos:+.1f} microsteps{spacing}")
        positions.append(reg_pos)
        # Nudge clear of the just-caught index so the next sweep finds the next.
        cmd(sock, f'MOVE({ONE_REV // 4}) AXIS({STEP_AX[ax]})')
        wait_idle(sock, STEP_AX[ax])

    if len(positions) >= 2:
        spans = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
        avg = sum(spans) / len(spans)
        print(f"\n  Mean index spacing: {avg:+.1f} microsteps "
              f"(expect ~{ONE_REV} = 1 motor rev).")
        if abs(abs(avg) - ONE_REV) > 0.02 * ONE_REV:
            print("  WARNING: spacing is not ~1 rev -- check encoder CPR / UNITS.")
    return True


def phase_b(sock, ax, reps):
    """Approach ONE index from the same side `reps` times; report scatter."""
    print("\n" + "=" * 60)
    print(f"PHASE B: repeatability ({reps} approaches, same index, same side)")
    print("=" * 60)
    sa = STEP_AX[ax]
    captures = []
    for i in range(reps):
        # Back off < 1 rev so we re-approach the SAME index from the - side.
        cmd(sock, f'MOVE({-BACKOFF}) AXIS({sa})')
        wait_idle(sock, sa)
        time.sleep(SETTLE)
        reg_pos, ok = seek_index(sock, ax)
        if not ok:
            print(f"  Approach {i+1}: index not recaptured -- aborting Phase B.")
            return
        rel = "" if not captures else f"   delta: {reg_pos - captures[0]:+.2f}"
        print(f"  Approach {i+1}: REG_POS = {reg_pos:+.2f}{rel}")
        captures.append(reg_pos)

    if captures:
        lo, hi = min(captures), max(captures)
        mean = sum(captures) / len(captures)
        ptp = hi - lo
        print(f"\n  REG_POS mean {mean:+.2f}, range {lo:+.2f}..{hi:+.2f}, "
              f"peak-to-peak {ptp:.2f} microsteps ({ptp/STEP_UNITS:.3f} full-steps).")
        print("  (Sub-step peak-to-peak = a solid index datum.)")


def run_axis(sock, ax, reps):
    print("\n" + "#" * 60)
    print(f"# AXIS {ax} ({AXIS_NAME[ax]}): step={STEP_AX[ax]} enc={ENC_AX[ax]} "
          f"fwd_in={FWD_INP[ax]} rev_in={REV_INP[ax]}")
    print("#" * 60)
    configure_axis(sock, ax)
    prompt(f"Axis {ax} ({AXIS_NAME[ax]}) ready. Stage clear and roughly mid-travel? "
           f"About to creep FORWARD seeking the index")
    if not phase_a(sock, ax):
        return
    phase_b(sock, ax, reps)
    cmd(sock, f'SPEED AXIS({STEP_AX[ax]}) = {RUN_SPEED}')   # restore
    print(f"\nAxis {ax} ({AXIS_NAME[ax]}) index verification done.")


def main():
    args = sys.argv[1:]
    reps = 6
    if '--reps' in args:
        i = args.index('--reps')
        reps = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    axes = [int(a) for a in args] if args else [2]
    for ax in axes:
        if ax not in (0, 1, 2, 3):
            print(f"Bad axis {ax} (expected 0..3).")
            return

    print("=" * 60)
    print("Encoder Z-Index Verification")
    print("=" * 60)
    print(f"Axes to test: {', '.join(f'{a} ({AXIS_NAME[a]})' for a in axes)}")
    print(f"Repeatability approaches per axis: {reps}")

    sock = connect()
    print("Connected.")
    try:
        if estop_pressed(sock):
            prompt("E-stop is PRESSED. Clear the stage, release E-stop, then continue")
        cmd(sock, 'WDOG = ON', 'Enable drives')
        for ax in axes:
            run_axis(sock, ax, reps)
        print("\n" + "=" * 60)
        print("All requested axes complete.")
    except KeyboardInterrupt:
        print("\n\nAborted by user. Stopping motion...")
        for ax in axes:
            try:
                send_cmd(sock, f'CANCEL AXIS({STEP_AX[ax]})')
            except Exception:
                pass
    finally:
        # Leave WDOG as-is (STARTUP may own it); just ensure no motion is queued.
        sock.close()
        print("Disconnected. (Drives left enabled; press E-stop to disable.)")


if __name__ == '__main__':
    main()
