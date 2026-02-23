"""Upload MC_CONFIG.bas to MC508 via telnet using EDPROG1 (!) commands."""
import socket
import time
import sys

HOST = '192.168.0.250'
PORT = 23

def recv_all(sock, timeout=1.0):
    sock.settimeout(timeout)
    data = b''
    while True:
        try:
            d = sock.recv(4096)
            if not d:
                break
            data += d
        except socket.timeout:
            break
    return data

def send_cmd(sock, cmd):
    """Send a command, wait for response, return cleaned text."""
    recv_all(sock, timeout=0.1)  # flush
    sock.sendall((cmd + '\r').encode())
    time.sleep(0.3)
    raw = recv_all(sock, timeout=1.0)
    text = raw.decode(errors='replace')
    lines = text.replace('\r\n', '\n').split('\n')
    filtered = [l for l in lines if l.strip() and l.strip() != '>>' and l.strip() != cmd.strip()]
    return '\n'.join(filtered).strip()

def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'stage/MC_CONFIG.bas'

    with open(config_file, 'r') as f:
        lines = f.readlines()

    # Filter to actual BASIC lines (skip comment-only and blank lines)
    program_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("'"):
            program_lines.append(stripped)

    if not program_lines:
        print("No program lines found in", config_file)
        return

    print(f"Config file: {config_file}")
    print(f"Program lines to upload:")
    for pl in program_lines:
        print(f"  {pl}")

    # EDPROG1 "!" syntax: NO space after "!"
    # !MC_CONFIG,N         -> line count
    # !MC_CONFIG,0 D       -> delete line 0
    # !MC_CONFIG,0 I,text  -> insert text at line 0
    # !MC_CONFIG,0,10 L    -> list lines 0-10
    # !MC_CONFIG,M          -> commit to flash
    PROG = 'MC_CONFIG'

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)

    try:
        s.connect((HOST, PORT))
        print(f"\nConnected to {HOST}:{PORT}")
        time.sleep(1)
        recv_all(s, timeout=1.0)

        # Select MC_CONFIG
        resp = send_cmd(s, f'SELECT {PROG}')
        print(f"SELECT {PROG} -> {resp}")

        # Get current line count
        resp = send_cmd(s, f'!{PROG},N')
        print(f"Current line count -> {resp}")

        try:
            nlines = int(resp.strip())
        except ValueError:
            nlines = 0

        # Delete existing lines
        if nlines > 0:
            print(f"Deleting {nlines} existing lines...")
            for i in range(nlines):
                resp = send_cmd(s, f'!{PROG},0D')
                if '%' in resp:
                    print(f"  Delete error: {resp}")
                    break

        # Insert new lines
        print("Inserting lines...")
        for i, pl in enumerate(program_lines):
            cmd = f'!{PROG},{i}I,{pl}'
            resp = send_cmd(s, cmd)
            if resp and '%' in resp:
                print(f"  ERROR on line {i} '{pl}': {resp}")
                return
            print(f"  Line {i}: {pl} -> OK")

        # Verify
        resp = send_cmd(s, f'!{PROG},N')
        print(f"\nLine count after insert -> {resp}")

        resp = send_cmd(s, f'!{PROG},0,10L')
        print(f"Listing:\n{resp}")

        # Commit to flash
        print("\nCommitting to flash...")
        resp = send_cmd(s, f'!{PROG},M')
        time.sleep(2)
        # Flush any delayed output
        extra = recv_all(s, timeout=2.0).decode(errors='replace').strip()
        if resp:
            print(f"Commit -> {resp}")
        if extra:
            extra_lines = [l for l in extra.split('\r\n') if l.strip() and l.strip() != '>>']
            if extra_lines:
                print('\n'.join(extra_lines))
        print("Commit -> done")

        # Verify DIR
        resp = send_cmd(s, 'DIR')
        print(f"\nDIR:\n{resp}")

        print("\nDone! Power cycle the controller to apply ATYPE changes.")
        print("Then verify with:")
        print("  python trio_cmd.py \"BASE(0)\" \"PRINT ATYPE\" \"BASE(4)\" \"PRINT ATYPE\"")

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
    finally:
        s.close()

if __name__ == '__main__':
    main()
