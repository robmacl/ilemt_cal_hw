"""Send commands to MC508 via telnet and print responses.

Usage:
    python trio_cmd.py [options] "CMD1" "CMD2" ...

Options:
    --debug     Show raw hex data
    --port N    Use port N (default 23)
    --wait N    Wait N seconds after connect (default 2)
"""
import socket
import sys
import time

HOST = '192.168.0.250'
PORT = 23
TIMEOUT = 5

def recv_all(sock, timeout=1.0):
    """Read all available data from socket."""
    sock.settimeout(timeout)
    data = b''
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            d = sock.recv(4096)
            if not d:
                break
            data += d
        except socket.timeout:
            break
    return data

def strip_telnet(data):
    """Strip telnet IAC negotiation sequences."""
    result = bytearray()
    i = 0
    while i < len(data):
        if data[i] == 0xFF and i + 1 < len(data):
            if data[i+1] == 0xFF:
                result.append(0xFF)  # Escaped 0xFF
                i += 2
            elif i + 2 < len(data):
                i += 3  # IAC + cmd + option
            else:
                i += 2
        else:
            result.append(data[i])
            i += 1
    return bytes(result)

def negotiate_telnet(sock, raw_data):
    """Respond to telnet negotiation requests."""
    i = 0
    responses = bytearray()
    while i < len(raw_data):
        if raw_data[i] == 0xFF and i + 2 < len(raw_data):
            cmd = raw_data[i+1]
            opt = raw_data[i+2]
            if cmd == 0xFD:  # DO -> respond WILL (agree to echo, etc)
                responses.extend([0xFF, 0xFB, opt])
            elif cmd == 0xFB:  # WILL -> respond DO
                responses.extend([0xFF, 0xFD, opt])
            i += 3
        else:
            i += 1
    if responses:
        sock.sendall(bytes(responses))

def send_cmd(sock, cmd, debug=False):
    """Send a command and return the response."""
    recv_all(sock, timeout=0.1)  # flush
    sock.sendall((cmd + '\r').encode())
    time.sleep(0.5)
    raw = recv_all(sock, timeout=1.5)
    if debug:
        print(f"   Raw ({len(raw)} bytes): {raw[:200].hex()}")
        if raw:
            print(f"   Repr: {repr(raw[:200])}")
    clean = strip_telnet(raw)
    text = clean.decode(errors='replace')
    # Remove echo of our command
    lines = text.split('\r\n') if '\r\n' in text else text.split('\n')
    filtered = [l.rstrip() for l in lines if l.strip() and not l.strip().startswith(cmd.strip()[:20])]
    return '\n'.join(filtered).strip()

def main():
    args = sys.argv[1:]
    debug = '--debug' in args
    if debug:
        args.remove('--debug')

    port = PORT
    if '--port' in args:
        idx = args.index('--port')
        port = int(args[idx + 1])
        args = args[:idx] + args[idx+2:]

    wait_time = 2
    if '--wait' in args:
        idx = args.index('--wait')
        wait_time = float(args[idx + 1])
        args = args[:idx] + args[idx+2:]

    commands = args if args else ['PRINT "Hello MC508"']

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)

    try:
        s.connect((HOST, port))
        print(f"Connected to {HOST}:{port}")

        # Wait for controller to send something
        time.sleep(wait_time)
        banner_raw = recv_all(s, timeout=2.0)

        if debug:
            print(f"Initial data ({len(banner_raw)} bytes): {banner_raw[:200].hex()}")
            if banner_raw:
                print(f"  Repr: {repr(banner_raw[:200])}")

        if banner_raw:
            negotiate_telnet(s, banner_raw)
            time.sleep(0.3)
            recv_all(s, timeout=0.3)  # flush negotiation response

            banner = strip_telnet(banner_raw)
            if banner.strip():
                print(f"Banner: {banner.decode(errors='replace').strip()}")

        # Send each command
        for cmd in commands:
            print(f"\n>> {cmd}")
            result = send_cmd(s, cmd, debug=debug)
            if result:
                print(result)
            else:
                print("(no response)")

    except ConnectionRefusedError:
        print(f"Connection refused on port {port}")
    except socket.timeout:
        print(f"Connection timed out")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
    finally:
        s.close()

if __name__ == '__main__':
    main()
