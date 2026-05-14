#!/usr/bin/env python3
"""
Standalone rigctld diagnostic tool
Tests if rigctld can start and connect to radio
"""

import subprocess
import socket
import time
import os
import sys

def test_rigctld(com_port, baud_rate):
    print("=" * 60)
    print(f"rigctld Diagnostic - Testing {com_port} at {baud_rate} baud")
    print("=" * 60)

    # Check for environment variable override first
    rigctld_override = os.environ.get('RIGCTLD_PATH')

    # Try bundled first, then system-wide installation
    bundled_path = os.path.join(os.path.dirname(__file__), 'hamlib', 'bin', 'rigctld.exe')
    system_path = r'C:\Program Files\hamlib-w64-4.7.1\bin\rigctld.exe'

    print(f"\n1. Checking rigctld.exe...")
    rigctld_path = None

    if rigctld_override and os.path.exists(rigctld_override):
        rigctld_path = rigctld_override
        print(f"[OK] Using override: {rigctld_path}")
    elif os.path.exists(bundled_path):
        rigctld_path = bundled_path
        print(f"[OK] Found bundled: {rigctld_path}")
    elif os.path.exists(system_path):
        rigctld_path = system_path
        print(f"[OK] Found system-wide: {rigctld_path}")
    else:
        print(f"[FAIL] rigctld.exe not found at:")
        if rigctld_override:
            print(f"       {rigctld_override} (override)")
        print(f"       {bundled_path}")
        print(f"       {system_path}")
        return False

    # Try to start rigctld
    print(f"\n2. Starting rigctld...")
    cmd = [
        rigctld_path,
        '-m', '3081',      # IC-7300
        '-r', com_port,
        '-s', str(baud_rate),
        '-C', 'civ_address=0xA2',
        '-t', '4532'
    ]
    print(f"Command: {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print("[OK] rigctld process started")
    except Exception as e:
        print(f"[FAIL] Could not start rigctld: {e}")
        return False

    # Wait for startup
    print(f"\n3. Waiting for rigctld to initialize...")
    time.sleep(2)

    # Test connection to port 4532
    print(f"\n4. Testing connection to localhost:4532...")
    for attempt in range(5):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(('localhost', 4532))

            # Send frequency query
            print(f"   [OK] Connected! Sending frequency query...")
            sock.sendall(b'f\n')
            response = sock.recv(1024).decode().strip()
            sock.close()

            if response:
                freq_hz = float(response)
                freq_mhz = freq_hz / 1e6
                print(f"   [OK] Got frequency: {freq_mhz:.4f} MHz")
                print("\n" + "=" * 60)
                print("[SUCCESS] rigctld is working!")
                print("=" * 60)
                proc.terminate()
                return True
            else:
                print(f"   [FAIL] No response from radio")

        except socket.timeout:
            print(f"   Attempt {attempt+1}: Connection timeout (port 4532 not responding)")
            time.sleep(0.5)
        except Exception as e:
            print(f"   Attempt {attempt+1}: {e}")
            time.sleep(0.5)

    print("\n" + "=" * 60)
    print("[FAIL] Could not connect to radio")
    print("=" * 60)
    print("\nTroubleshooting:")
    print("  • Radio is powered ON?")
    print("  • USB cable connected?")
    print("  • Radio CI-V baud rate matches (19200 or 9600)?")
    print("  • Radio CI-V address is 0xA2?")
    print("  • No other software using COM port?")

    proc.terminate()
    return False

if __name__ == '__main__':
    # Default to IC-7300 on COM6 at 9600 baud
    com_port = 'COM6'
    baud_rate = 9600

    if len(sys.argv) > 1:
        com_port = sys.argv[1]
    if len(sys.argv) > 2:
        baud_rate = int(sys.argv[2])

    success = test_rigctld(com_port, baud_rate)
    sys.exit(0 if success else 1)
