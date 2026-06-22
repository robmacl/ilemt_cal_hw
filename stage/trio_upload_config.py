"""Upload a TrioBASIC program to the MC508 over telnet, and optionally run it
or set it to autorun at power-up.

Uses the EDPROG1 ("!") line editor to insert the program line-by-line, then
commits to flash. Generalized from the original MC_CONFIG-only uploader.

Examples:
    # Upload MC_CONFIG (ATYPE assignments), then power-cycle to apply:
    python trio_upload_config.py MC_CONFIG.bas

    # Upload STARTUP and RUN it now for a manual test (not persistent):
    python trio_upload_config.py STARTUP.BAS --run

    # Same, on a specific process, watching with the monitor in another shell:
    python trio_upload_config.py STARTUP.BAS --run --proc 2

    # Once happy, make STARTUP run automatically at power-up:
    python trio_upload_config.py STARTUP.BAS --autorun

    # Stop a running program (no upload):
    python trio_upload_config.py STARTUP.BAS --no-upload --stop

Program name on the controller is derived from the filename (STARTUP.BAS ->
STARTUP), or set with --name.

NOTE: a program cannot be edited while it is running. This tool issues
STOP "NAME" before uploading; use --halt to stop ALL programs first if the
controller still refuses (it won't let you edit while anything runs).

NOTE: long uploads (e.g. STARTUP) occasionally fail mid-insert with
"%[COMMAND 3] Error programming Flash" - a transient flash-write error that
shows up under sustained rapid line inserts and is not seen on short files
like MC_CONFIG. The uploader now auto-retries the entire upload a few times on
this error; because every attempt deletes all existing lines before
re-inserting, a retry is safe (no duplicate or shifted lines). If it still
fails after the retries, just run it again, or add --halt.
"""
import argparse
import os
import sys
import time

from trio_cmd import connect, recv_all, recv_until_prompt, strip_telnet

HOST = '192.168.1.250' # factory default is 192.168.0.250

# Transient flash-write error seen mid-insert on long uploads; retryable.
FLASH_ERR = 'Error programming Flash'


def is_flash_error(resp):
    """True if a controller response is the transient flash-write error."""
    return bool(resp) and FLASH_ERR in resp


def send_cmd(sock, cmd, settle=0.0, timeout=3.0):
    """Send a command and return the cleaned response.

    Prompt-based: returns as soon as the controller emits the '>>' prompt, so
    a 228-line insert takes a few seconds instead of a fixed delay per line.
    'settle' adds an optional extra wait (used for the slow flash commit).
    """
    recv_all(sock, timeout=0.05)  # flush
    sock.sendall((cmd + '\r').encode())
    if settle:
        time.sleep(settle)
    raw = recv_until_prompt(sock, timeout=timeout)
    text = strip_telnet(raw).decode(errors='replace')
    lines = text.replace('\r\n', '\n').split('\n')
    filtered = [l for l in lines
                if l.strip() and l.strip() != '>>' and l.strip() != cmd.strip()]
    return '\n'.join(filtered).strip()


def prog_name_from_file(path):
    base = os.path.basename(path)
    name = os.path.splitext(base)[0]
    return name.upper()


def load_program_lines(path, keep_comments=False):
    """Read a .bas file into upload-ready lines.

    Skips blank lines and (by default) comment-only lines. Inline comments on
    code lines are kept so the on-controller listing stays readable for
    debugging. Leading indentation is stripped (cosmetic in TrioBASIC).
    """
    out = []
    with open(path, 'r') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("'") and not keep_comments:
                continue
            out.append(s)
    return out


def upload_program(sock, prog, lines, list_after=True):
    """Replace program 'prog' on the controller with 'lines' and commit."""
    # SELECT creates the program if it doesn't exist (as BASIC type).
    resp = send_cmd(sock, f'SELECT {prog}')
    if resp:
        print(f"  SELECT {prog} -> {resp}")

    # Current line count, then delete existing lines (always from line 0).
    resp = send_cmd(sock, f'!{prog},N')
    try:
        nlines = int(resp.strip())
    except (ValueError, AttributeError):
        nlines = 0
    if nlines > 0:
        print(f"  Deleting {nlines} existing lines...")
        for _ in range(nlines):
            r = send_cmd(sock, f'!{prog},0D')
            if is_flash_error(r):
                print("  Flash write error during delete.")
                return 'flash'
            if r and '%' in r:
                print(f"  Delete error: {r}")
                return False

    # Insert new lines. EDPROG takes the text after 'I,' verbatim, so commas
    # and quotes inside the BASIC line are preserved.
    n = len(lines)
    print(f"  Inserting {n} lines...")
    for i, pl in enumerate(lines):
        r = send_cmd(sock, f'!{prog},{i}I,{pl}')
        if is_flash_error(r):
            print(f"\n  Flash write error on line {i}.")
            return 'flash'
        if r and '%' in r:
            print(f"\n  ERROR on line {i}: {pl}\n    -> {r}")
            return False
        if (i + 1) % 20 == 0 or i + 1 == n:
            sys.stdout.write(f"\r    {i + 1}/{n}")
            sys.stdout.flush()
    print()

    # Verify count.
    resp = send_cmd(sock, f'!{prog},N')
    print(f"  Line count after insert -> {resp}")

    if list_after:
        resp = send_cmd(sock, f'!{prog},0,{len(lines)}L', settle=0.6, timeout=2.0)
        print(f"  Listing:\n{resp}")

    # Commit to flash (slower; give it time).
    print("  Committing to flash...")
    resp = send_cmd(sock, f'!{prog},M', settle=2.0, timeout=3.0)
    if is_flash_error(resp):
        print("  Flash write error during commit.")
        return 'flash'
    if resp:
        print(f"  Commit -> {resp}")
    print("  Commit done.")
    return True


def stop_program(sock, prog):
    r = send_cmd(sock, f'STOP "{prog}"')
    print(f"  STOP \"{prog}\" -> {r if r else 'ok'}")


def run_program(sock, prog, proc=None):
    cmd = f'RUN "{prog}"' + (f', {proc}' if proc is not None else '')
    r = send_cmd(sock, cmd, settle=0.5)
    print(f"  {cmd} -> {r if r else 'ok'}")


def set_runtype(sock, prog, proc=None, mode=1):
    cmd = f'RUNTYPE "{prog}", {mode}' + (f', {proc}' if proc is not None else '')
    r = send_cmd(sock, cmd)
    print(f"  {cmd} -> {r if r else 'ok'}")


def main():
    ap = argparse.ArgumentParser(description="Upload/run a TrioBASIC program on the MC508")
    ap.add_argument("progfile", nargs="?", default="MC_CONFIG.bas",
                    help="path to the .bas file (default: MC_CONFIG.bas)")
    ap.add_argument("--name", help="program name on controller (default: from filename)")
    ap.add_argument("--host", default=HOST, help=f"controller IP (default {HOST})")
    ap.add_argument("--keep-comments", action="store_true",
                    help="upload comment-only lines too (default: skip them)")
    ap.add_argument("--no-upload", action="store_true",
                    help="skip the upload step (use with --run/--stop/--autorun)")
    ap.add_argument("--halt", action="store_true",
                    help="HALT all programs before editing")
    ap.add_argument("--stop", action="store_true",
                    help="STOP the program (also done automatically before upload)")
    ap.add_argument("--run", action="store_true",
                    help="RUN the program now (manual test, not persistent)")
    ap.add_argument("--autorun", action="store_true",
                    help='set RUNTYPE NAME,1 so it runs at power-up')
    ap.add_argument("--proc", type=int, default=None,
                    help="process number for --run / --autorun (default: controller chooses)")
    args = ap.parse_args()

    prog = args.name if args.name else prog_name_from_file(args.progfile)

    lines = None
    if not args.no_upload:
        if not os.path.exists(args.progfile):
            print(f"File not found: {args.progfile}")
            return 1
        lines = load_program_lines(args.progfile, keep_comments=args.keep_comments)
        if not lines:
            print(f"No program lines found in {args.progfile}")
            return 1

    sock = connect(host=args.host)
    print(f"\nProgram name: {prog}")

    try:
        if args.halt:
            r = send_cmd(sock, 'HALT')
            print(f"  HALT -> {r if r else 'ok'}")

        # A program can't be edited while running; stop the target first.
        if not args.no_upload or args.stop:
            stop_program(sock, prog)

        if not args.no_upload:
            # upload_program returns True (ok), 'flash' (transient flash-write
            # error, retryable), or False (deterministic failure). A retry
            # deletes all lines first, so it cannot leave duplicates.
            FLASH_RETRIES = 3
            status = False
            for attempt in range(1, FLASH_RETRIES + 2):
                status = upload_program(sock, prog, lines)
                if status is True or status is False:
                    break
                if attempt <= FLASH_RETRIES:
                    print(f"  Transient flash error; retrying whole upload "
                          f"(attempt {attempt + 1}/{FLASH_RETRIES + 1})...")
                    time.sleep(1.0)
            if status is not True:
                print("\nUpload FAILED.")
                return 1

        if args.run:
            print("\nStarting program (manual run)...")
            run_program(sock, prog, args.proc)
            print(f"  '{prog}' is running. Watch it with:")
            print("    python homing_monitor.py")

        if args.autorun:
            print("\nSetting autorun...")
            set_runtype(sock, prog, args.proc, mode=1)
            print("  NOTE: autorun requires ALL programs to compile cleanly.")
            print("  NOTE: STARTUP sets WDOG=ON at power-up (drives enabled, holding).")

        # Guidance.
        print()
        if prog == "MC_CONFIG" and not args.no_upload:
            print("MC_CONFIG uploaded. POWER-CYCLE the controller to apply ATYPE.")
            print('Then verify:  python trio_cmd.py "?ATYPE AXIS(2)" "?ATYPE AXIS(5)"')
        elif not args.run and not args.autorun and not args.no_upload:
            print(f"{prog} uploaded. To test it manually:")
            print(f"    python trio_upload_config.py {args.progfile} --no-upload --run")
            print("To make it run at power-up:")
            print(f"    python trio_upload_config.py {args.progfile} --no-upload --autorun")

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return 1
    finally:
        sock.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
