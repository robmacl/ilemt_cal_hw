"""Live monitor + control for the MC508 homing program (STARTUP.BAS).

Polls the status VRs over telnet and renders a one-line live dashboard, so
you can watch homing progress and faults without copy-pasting from a terminal.
Optionally issues a HOME_REQ and/or clears a fault latch.

Usage:
    python homing_monitor.py                 # just watch
    python homing_monitor.py --home 7         # home X+Y+Z (bitmask), then watch
    python homing_monitor.py --home all       # home all 4 axes
    python homing_monitor.py --clear          # clear fault latch, then watch

Bitmask: bit0=X bit1=Y bit2=Z bit3=Rz  (so 7 = X+Y+Z, 15 = all).

The VR map mirrors the header of STARTUP.BAS. Keep the two in sync.
"""
import argparse
import sys
import time

from trio_cmd import connect, send_cmd

# --- VR map (must match STARTUP.BAS) ---
VR_HOME_REQ = 100
VR_CLR_FAULT = 101
VR_HOMED = 110
VR_BUSY = 111
VR_ESTOP = 112
VR_FAULT = 113
VR_FAULT_AXIS = 114
VR_STATE = 115
VR_CUR_AXIS = 116
VR_RANGE_STP = 120  # +axis
VR_RANGE_ENC = 124  # +axis
VR_MSG_BASE = 200

AXIS_NAMES = ["X", "Y", "Z", "Rz"]

FAULT_TEXT = {
    0: "OK",
    1: "NEG_LIMIT_NOT_FOUND",
    2: "POS_LIMIT_NOT_FOUND",
    4: "RANGE_TOO_SMALL",
    6: "ESTOP_ABORT",
    7: "TIMEOUT",
}

STATE_TEXT = {
    0: "idle",
    1: "init_done",
    10: "seek_neg",
    11: "seek_pos",
    12: "to_mid",
    13: "axis_homed",
    90: "FAULT",
    91: "ESTOP_ABORT",
}


def get_vr(sock, n):
    """Read VR(n) as a float, or None on parse failure."""
    r = send_cmd(sock, f"PRINT VR({n})")
    try:
        return float(r.strip().split()[-1])
    except (ValueError, AttributeError, IndexError):
        return None


def set_vr(sock, n, value):
    send_cmd(sock, f"VR({n})={value}")


def get_detail(sock):
    """Read the packed VRSTRING detail message."""
    r = send_cmd(sock, f"PRINT VRSTRING({VR_MSG_BASE})")
    return r.strip() if r else ""


def mask_str(value):
    """Render a 4-bit axis bitmask like 'X Y Z -'."""
    if value is None:
        return "????"
    v = int(value)
    return " ".join(AXIS_NAMES[i] if (v >> i) & 1 else "-" for i in range(4))


def main():
    ap = argparse.ArgumentParser(description="MC508 homing monitor")
    ap.add_argument("--home", metavar="MASK",
                    help="issue HOME_REQ: a bitmask integer, or 'all'")
    ap.add_argument("--clear", action="store_true",
                    help="clear fault/e-stop latch before watching")
    ap.add_argument("--interval", type=float, default=0.25,
                    help="poll interval seconds (default 0.25)")
    args = ap.parse_args()

    sock = connect()
    print("Connected. Ctrl-C to stop.\n")

    try:
        if args.clear:
            set_vr(sock, VR_CLR_FAULT, 1)
            print("Fault latch clear requested.")

        if args.home is not None:
            mask = 15 if args.home.lower() == "all" else int(args.home, 0)
            set_vr(sock, VR_HOME_REQ, mask)
            print(f"HOME_REQ = {mask} ({mask_str(mask)})\n")

        last_detail = None
        while True:
            homed = get_vr(sock, VR_HOMED)
            busy = get_vr(sock, VR_BUSY)
            estop = get_vr(sock, VR_ESTOP)
            fault = get_vr(sock, VR_FAULT)
            faxis = get_vr(sock, VR_FAULT_AXIS)
            state = get_vr(sock, VR_STATE)
            curax = get_vr(sock, VR_CUR_AXIS)

            st = STATE_TEXT.get(int(state) if state is not None else -1, f"?{state}")
            fc = int(fault) if fault is not None else -1
            ft = FAULT_TEXT.get(fc, f"?{fc}")
            cur = AXIS_NAMES[int(curax)] if (curax is not None and 0 <= curax <= 3) else "-"
            es = "E-STOP" if estop else "      "

            line = (f"\r[{st:<11}] cur={cur:<2} homed=[{mask_str(homed)}] "
                    f"busy={int(busy) if busy is not None else '?'} "
                    f"fault={ft:<20} {es}")
            sys.stdout.write(line)
            sys.stdout.flush()

            # Print the detail string on a new line whenever it changes.
            detail = get_detail(sock)
            if detail and detail != last_detail:
                sys.stdout.write("\n   -> " + detail + "\n")
                sys.stdout.flush()
                last_detail = detail

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
