"""Interactive Z axis bring-up and test script.

Walks through configuration and testing of the Z axis step by step,
with user prompts before anything that moves the motor.

Prerequisites:
  - MC_CONFIG.bas uploaded and controller power-cycled
  - Z axis encoder cable on port 2, stepper cable on port 5
  - E-stop engaged (will prompt to release)

Usage:
    python stage/z_axis_test.py
"""
import sys
import time
from trio_cmd import connect, send_cmd

# --- Z axis configuration ---
ENC_AXIS = 2       # Encoder axis (ATYPE 76, port 2)
STEP_AXIS = 5      # Stepper axis (ATYPE 43, port 5)

# Limit switch inputs (from encoder port 2: pin 9 = 16+2*2, pin 20 = 17+2*2)
POS_LIMIT_IN = 20  # Forward limit
NEG_LIMIT_IN = 21  # Reverse limit

# Hardware: US Digital E6-2500 encoder, 200-step motor w/ 1/32 microstep
# Lead screw: 0.2 in/rev = 5.08 mm/rev
ENCODER_CPR = 2500
ENCODER_COUNTS_PER_REV = ENCODER_CPR * 4        # 10,000 (quadrature)
MICROSTEPS_PER_REV = 200 * 32                    # 6,400
STEP_MULTIPLIER = 16                             # MC508 FlexAxis internal
STEP_COUNTS_PER_REV = MICROSTEPS_PER_REV * STEP_MULTIPLIER  # 102,400
MM_PER_REV = 0.2 * 25.4                          # 5.08 mm

# Negative because encoder counts in the opposite direction to stepper
ENC_UNITS = -ENCODER_COUNTS_PER_REV / MM_PER_REV  # ~-1968.5 counts/mm
STEP_UNITS = STEP_COUNTS_PER_REV / MM_PER_REV    # ~20157.5 counts/mm

SPEED = 15.0    # mm/s
ACCEL = 50.0    # mm/s^2 (0 to 15 mm/s in 0.3s)
DECEL = 50.0    # mm/s^2
CREEP = 1.0     # mm/s (for homing)

HOMING_SPEED = 5.0   # mm/s (slow approach to limit)
HOMING_BACKOFF = 2.0 # mm (back off from limit switch)


def cmd(sock, command, label=None):
    """Send command, print it and the response."""
    if label:
        print(f"\n--- {label} ---")
    print(f"  >> {command}")
    result = send_cmd(sock, command)
    if result:
        print(f"  {result}")
    return result


def prompt(msg):
    """Prompt user and wait for Enter. Ctrl-C aborts."""
    try:
        input(f"\n>>> {msg} [Enter to continue, Ctrl-C to abort] ")
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)


def wait_idle(sock, axis, timeout=10):
    """Wait for axis to become idle."""
    time.sleep(0.5)
    for i in range(int(timeout / 0.2)):
        idle = send_cmd(sock, f'?IDLE AXIS({axis})')
        if idle and '1' in idle:
            return True
        time.sleep(0.2)
    print(f"  WARNING: Axis {axis} did not become idle within {timeout}s")
    return False


def read_float(sock, query):
    """Send a query and return the result as a float, or None."""
    result = send_cmd(sock, query)
    try:
        return float(result.strip())
    except (ValueError, AttributeError):
        return None


def main():
    print("=" * 60)
    print("Z Axis Bring-Up Test")
    print("=" * 60)

    print(f"\nEncoder axis:  {ENC_AXIS} (port {ENC_AXIS})")
    print(f"Stepper axis:  {STEP_AXIS} (port {STEP_AXIS})")
    print(f"Pos limit:     input {POS_LIMIT_IN}")
    print(f"Neg limit:     input {NEG_LIMIT_IN}")
    print(f"Enc UNITS:     {ENC_UNITS:.1f} counts/mm")
    print(f"Step UNITS:    {STEP_UNITS:.1f} counts/mm (assumes x{STEP_MULTIPLIER} multiplier)")

    # ---- Connect ----
    print("\nConnecting to MC508...")
    sock = connect()
    print("Connected.\n")

    try:
        # ---- Step 1: Verify ATYPE ----
        atype_enc = cmd(sock, f'?ATYPE AXIS({ENC_AXIS})', 'Verify ATYPE')
        atype_step = cmd(sock, f'?ATYPE AXIS({STEP_AXIS})')
        print(f"\n  Encoder axis {ENC_AXIS} ATYPE: {atype_enc}  (expect 76)")
        print(f"  Stepper axis {STEP_AXIS} ATYPE: {atype_step}  (expect 43)")

        if '76' not in str(atype_enc) or '43' not in str(atype_step):
            print("\n  WARNING: ATYPE mismatch! Upload MC_CONFIG.bas and power cycle.")
            print("    python stage/trio_upload_config.py stage/MC_CONFIG.bas")
            prompt("Continue anyway?")

        # ---- Step 2: Read limit switches ----
        print("\n" + "=" * 60)
        in_pos = cmd(sock, f'?IN({POS_LIMIT_IN})', 'Read limit switches')
        in_neg = cmd(sock, f'?IN({NEG_LIMIT_IN})')
        print(f"\n  Pos limit (input {POS_LIMIT_IN}): {in_pos}")
        print(f"  Neg limit (input {NEG_LIMIT_IN}): {in_neg}")
        print("  (Expect 1 when away from limit, 0 at limit)")

        # ---- Step 3: Configure inputs ----
        # The raw sensor polarity already matches Trio's active-low convention:
        #   Away from limit → sensor high → MC508 reads 1 → FWD_IN not triggered
        #   At limit → sensor low → MC508 reads 0 → FWD_IN triggers (cancels move)
        # So INVERT_IN is NOT needed. Ensure it's OFF in case a previous run set it.
        print("\n" + "=" * 60)
        print("--- Configure inputs ---")
        cmd(sock, f'INVERT_IN({POS_LIMIT_IN}, OFF)')
        cmd(sock, f'INVERT_IN({NEG_LIMIT_IN}, OFF)')

        in_pos = cmd(sock, f'?IN({POS_LIMIT_IN})', 'Verify limits (no inversion)')
        in_neg = cmd(sock, f'?IN({NEG_LIMIT_IN})')
        print(f"\n  Pos limit: {in_pos}  (expect 1 when away from limit)")
        print(f"  Neg limit: {in_neg}  (expect 1 when away from limit)")

        # Assign limit inputs to stepper axis
        cmd(sock, f'FWD_IN AXIS({STEP_AXIS}) = {POS_LIMIT_IN}')
        cmd(sock, f'REV_IN AXIS({STEP_AXIS}) = {NEG_LIMIT_IN}')
        cmd(sock, f'DATUM_IN AXIS({ENC_AXIS}) = {NEG_LIMIT_IN}')
        print("  FWD_IN, REV_IN, DATUM_IN assigned.")

        # ---- Step 4: Configure motion parameters ----
        print("\n" + "=" * 60)
        print("--- Configure motion parameters ---")

        # Stepper axis
        cmd(sock, f'SERVO AXIS({STEP_AXIS}) = OFF')
        cmd(sock, f'UNITS AXIS({STEP_AXIS}) = {STEP_UNITS:.4f}')
        cmd(sock, f'SPEED AXIS({STEP_AXIS}) = {SPEED}')
        cmd(sock, f'ACCEL AXIS({STEP_AXIS}) = {ACCEL}')
        cmd(sock, f'DECEL AXIS({STEP_AXIS}) = {DECEL}')

        # INVERT_STEP has no effect on this controller — leave OFF.
        # Negative ENC_UNITS alone gives +1.0 ratio.
        # Convention: positive = down, negative = up.
        cmd(sock, f'INVERT_STEP AXIS({STEP_AXIS}) = OFF')

        # Encoder axis (read-only position feedback, no motion commands)
        cmd(sock, f'SERVO AXIS({ENC_AXIS}) = OFF')
        cmd(sock, f'UNITS AXIS({ENC_AXIS}) = {ENC_UNITS:.4f}')

        print("  Motion parameters set.")

        # ---- Step 5: Read initial positions ----
        print("\n" + "=" * 60)
        mpos_enc = cmd(sock, f'?MPOS AXIS({ENC_AXIS})', 'Initial positions')
        dpos_step = cmd(sock, f'?DPOS AXIS({STEP_AXIS})')
        mpos_step = cmd(sock, f'?MPOS AXIS({STEP_AXIS})')
        print(f"\n  Encoder MPOS (axis {ENC_AXIS}): {mpos_enc} mm")
        print(f"  Stepper DPOS (axis {STEP_AXIS}): {dpos_step} mm")
        print(f"  Stepper MPOS (axis {STEP_AXIS}): {mpos_step} mm")

        # Record initial positions for delta calculation
        enc_before = read_float(sock, f'?MPOS AXIS({ENC_AXIS})')
        dpos_before = read_float(sock, f'?DPOS AXIS({STEP_AXIS})')

        # ---- Step 6: Enable drives ----
        print("\n" + "=" * 60)
        prompt("Release E-stop, then press Enter to enable WDOG")
        cmd(sock, 'WDOG = ON', 'Enable drives')
        print("  WDOG enabled. Stepper drivers should be energized.")

        # ---- Step 7: Test move ----
        print("\n" + "=" * 60)
        test_dist = 0.5  # mm
        prompt(f"About to move Z axis {test_dist} mm. Stage must be clear of limits")

        print(f"\n--- Test move: {test_dist} mm ---")
        cmd(sock, f'MOVE({test_dist}) AXIS({STEP_AXIS})')

        # Wait for move to complete
        print("  Waiting for move to complete...")
        wait_idle(sock, STEP_AXIS)

        # Read positions after move
        enc_after = read_float(sock, f'?MPOS AXIS({ENC_AXIS})')
        dpos_after = read_float(sock, f'?DPOS AXIS({STEP_AXIS})')
        mpos_step_after = read_float(sock, f'?MPOS AXIS({STEP_AXIS})')

        print(f"\n--- Positions after move ---")
        print(f"  Stepper DPOS: {dpos_after} mm  (demanded)")
        print(f"  Stepper MPOS: {mpos_step_after} mm  (stepper count)")
        print(f"  Encoder MPOS: {enc_after} mm  (actual position)")

        if enc_before is not None and dpos_before is not None \
                and enc_after is not None and dpos_after is not None:
            d_enc = enc_after - enc_before
            d_dpos = dpos_after - dpos_before
            print(f"\n  Delta encoder: {d_enc:.4f} mm")
            print(f"  Delta stepper: {d_dpos:.4f} mm")
            if abs(d_dpos) > 0.001:
                ratio = d_enc / d_dpos
                print(f"  Encoder/Demanded ratio: {ratio:.4f}")
                print(f"  (Should be ~+1.0 with negative ENC_UNITS)")
                if abs(abs(ratio) - 1.0) > 0.05:
                    print(f"  WARNING: Ratio is not ~1.0. Check UNITS or x16 assumption.")
                if ratio < 0:
                    print(f"  WARNING: Negative ratio — check ENC_UNITS sign.")
            else:
                print("  WARNING: Stepper didn't move. Check WDOG and driver.")
        else:
            print("  (Could not parse position values for ratio check)")

        # ---- Step 8: Return to start ----
        prompt("Move back to start position?")
        cmd(sock, f'MOVE({-test_dist}) AXIS({STEP_AXIS})')
        wait_idle(sock, STEP_AXIS)

        mpos_enc = cmd(sock, f'?MPOS AXIS({ENC_AXIS})', 'Final position')
        print(f"  Encoder MPOS: {mpos_enc} mm  (should be near start)")

        # ---- Step 9: Home to negative limit ----
        print("\n" + "=" * 60)
        print("--- Homing ---")
        print("  Strategy: reverse to neg limit, back off, zero both axes.")
        print("  (DATUM(6) can't be used because stepper and encoder are on")
        print("   separate axes. Full Z-index homing needs custom REGIST code.)")
        prompt("About to home: reverse until neg limit triggers")

        # Save current speed, use homing speed
        cmd(sock, f'SPEED AXIS({STEP_AXIS}) = {HOMING_SPEED}')

        # Move a large distance in reverse — REV_IN (input 21) will stop it.
        # Negative direction = physically up. REV_IN = NEG_LIMIT_IN = input 21.
        cmd(sock, f'MOVE(-999) AXIS({STEP_AXIS})')
        print("  Moving toward reverse limit (up)...")

        # Wait for motion to stop (either limit will cancel the move)
        wait_idle(sock, STEP_AXIS)
        print("  Motion stopped.")

        # Check which limit we're on
        in_pos = read_float(sock, f'?IN({POS_LIMIT_IN})')
        in_neg = read_float(sock, f'?IN({NEG_LIMIT_IN})')
        print(f"  Input {POS_LIMIT_IN} (POS_LIMIT_IN): {int(in_pos) if in_pos is not None else '?'}")
        print(f"  Input {NEG_LIMIT_IN} (NEG_LIMIT_IN): {int(in_neg) if in_neg is not None else '?'}")
        if in_pos is not None and in_pos < 0.5:
            print(f"  -> Sitting on input {POS_LIMIT_IN}")
        if in_neg is not None and in_neg < 0.5:
            print(f"  -> Sitting on input {NEG_LIMIT_IN}")

        # Cancel any residual motion
        cmd(sock, f'CANCEL AXIS({STEP_AXIS})')

        # Back off from limit
        print(f"\n  Backing off {HOMING_BACKOFF} mm...")
        cmd(sock, f'MOVE({HOMING_BACKOFF}) AXIS({STEP_AXIS})')
        wait_idle(sock, STEP_AXIS)

        # Verify we're off the limit
        in_neg = read_float(sock, f'?IN({NEG_LIMIT_IN})')
        if in_neg is not None and in_neg < 0.5:
            print("  WARNING: Still on limit after backoff. Increase HOMING_BACKOFF.")

        # Zero both axes (DEFPOS sets both DPOS and MPOS to given value)
        cmd(sock, f'DEFPOS(0) AXIS({STEP_AXIS})')
        cmd(sock, f'DEFPOS(0) AXIS({ENC_AXIS})')
        print("  Both axes zeroed. Home position set.")

        # Read final positions
        enc_home = cmd(sock, f'?MPOS AXIS({ENC_AXIS})', 'Home position')
        dpos_home = cmd(sock, f'?DPOS AXIS({STEP_AXIS})')
        print(f"  Encoder MPOS: {enc_home} mm")
        print(f"  Stepper DPOS: {dpos_home} mm")

        # Restore normal speed
        cmd(sock, f'SPEED AXIS({STEP_AXIS}) = {SPEED}')

        # ---- Disable ----
        print("\n" + "=" * 60)
        cmd(sock, 'WDOG = OFF', 'Disable drives')
        print("\nTest complete.")

    except KeyboardInterrupt:
        print("\n\nAborted by user. Disabling drives...")
        try:
            send_cmd(sock, 'CANCEL AXIS(5)')
            send_cmd(sock, 'WDOG = OFF')
        except Exception:
            pass
    finally:
        sock.close()


if __name__ == '__main__':
    main()
