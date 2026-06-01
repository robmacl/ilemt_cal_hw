"""Live monitor + control for the MC508 homing program (STARTUP.BAS).

Polls the status VRs over telnet and renders a one-line live dashboard, so
you can watch homing progress and faults without copy-pasting from a terminal.
Optionally issues a HOME_REQ and/or clears a fault latch.

Usage:
    python homing_monitor.py                 # just watch
    python homing_monitor.py --range          # measured travel + enc/stp ratio
    python homing_monitor.py --inputs         # no-motion limit/e-stop toggle test
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


# Limit inputs per axis (see Configuration.md "Limit Switch Inputs").
# (pos/FWD input, neg/REV input)
LIMIT_INPUTS = [
    ("X", 16, 17),
    ("Y", 18, 19),
    ("Z", 20, 21),
    ("Rz", 22, 23),
]
ESTOP_INPUT = 0  # XA0: ON=released, OFF=pressed


def get_vr(sock, n):
    """Read VR(n) as a float, or None on parse failure."""
    r = send_cmd(sock, f"PRINT VR({n})")
    try:
        return float(r.strip().split()[-1])
    except (ValueError, AttributeError, IndexError):
        return None


def get_in(sock, n):
    """Read digital input IN(n) as 0/1, or None on parse failure."""
    r = send_cmd(sock, f"PRINT IN({n})")
    try:
        return int(float(r.strip().split()[-1]))
    except (ValueError, AttributeError, IndexError):
        return None


def inputs_view(sock, interval):
    """Live, no-motion display of e-stop + all limit inputs.

    Use this to confirm by hand that each limit switch toggles its input and
    that pos/neg are on the end you expect, BEFORE trusting a homing seek.
    Trip each switch manually and watch its marker flip.

    Convention reminder (Configuration.md): a limit reads 1 when AWAY from the
    limit and 0 when AT it. E-stop (XA0) reads 1 when released, 0 when pressed.
    """
    print("Live input monitor. Trip each switch by hand; Ctrl-C to stop.")
    print("  limit: 1=away  0=AT-LIMIT     e-stop: 1=released  0=PRESSED\n")
    while True:
        es = get_in(sock, ESTOP_INPUT)
        es_txt = "????"
        if es is not None:
            es_txt = "released" if es == 1 else "PRESSED "
        cells = []
        for name, pin_pos, pin_neg in LIMIT_INPUTS:
            p = get_in(sock, pin_pos)
            n = get_in(sock, pin_neg)
            pm = "AT" if p == 0 else ("--" if p == 1 else "??")
            nm = "AT" if n == 0 else ("--" if n == 1 else "??")
            cells.append(f"{name}: +{pm} -{nm}")
        line = f"\rE-stop[{es_txt}]  " + "  ".join(cells)
        sys.stdout.write(line)
        sys.stdout.flush()
        time.sleep(interval)


def range_view(sock):
    """One-shot print of measured per-axis travel (microsteps) and the
    encoder/stepper ratio (a free correctness check; should be ~1.0)."""
    print("Measured travel per axis (microsteps), from the last homing:")
    print(f"  {'axis':<4} {'stepper':>14} {'encoder':>14} {'enc/stp':>9}  ~mm/deg")
    for i, name in enumerate(AXIS_NAMES):
        stp = get_vr(sock, VR_RANGE_STP + i)
        enc = get_vr(sock, VR_RANGE_ENC + i)
        if stp is None or enc is None:
            print(f"  {name:<4} {'?':>14} {'?':>14}")
            continue
        ratio = (enc / stp) if stp else 0.0
        # microsteps -> physical: XYZ 5.08/6400 mm, Rz 2/6400 deg
        scale = (2.0 if i == 3 else 5.08) / 6400.0
        phys = abs(stp) * scale
        unit = "deg" if i == 3 else "mm"
        print(f"  {name:<4} {stp:>14.1f} {enc:>14.1f} {ratio:>9.5f}  {phys:.3f} {unit}")


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
    ap.add_argument("--inputs", action="store_true",
                    help="no-motion live view of e-stop + limit inputs (toggle test)")
    ap.add_argument("--range", action="store_true", dest="show_range",
                    help="print measured per-axis travel + enc/stp ratio, then exit")
    args = ap.parse_args()

    sock = connect()
    print("Connected. Ctrl-C to stop.\n")

    try:
        if args.show_range:
            range_view(sock)
            return
        if args.inputs:
            inputs_view(sock, args.interval)
            return
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
    except (ConnectionError, OSError) as e:
        print(f"\nConnection lost ({type(e).__name__}). The MC508 telnet command"
              " line allows only ONE connection at a time — did another tool"
              " (e.g. trio_upload_config.py) connect? Run them one at a time.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
