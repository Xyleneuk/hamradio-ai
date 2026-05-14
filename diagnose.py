#!/usr/bin/env python3
"""
Diagnostic script to debug radio connection issues
"""

import subprocess
import os
import sys

# Find rigctld: bundled first, then common installation paths
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(_BASE_DIR, 'hamlib', 'bin', 'rigctld.exe'),
    r'C:\Program Files\hamlib-w64-4.7.1\bin\rigctld.exe',
    r'C:\Program Files\hamlib-w64-4.6\bin\rigctld.exe',
    r'C:\Program Files\hamlib-w64-4.5\bin\rigctld.exe',
    r'C:\Program Files\hamlib\bin\rigctld.exe',
    r'C:\Program Files (x86)\hamlib\bin\rigctld.exe',
]
RIGCTLD_PATH = next((p for p in _CANDIDATES if os.path.exists(p)), None)

print("=" * 60)
print("IC-7300 Diagnostic Check")
print("=" * 60)

# Check if rigctld exists
print("\n1. Checking rigctld executable...")
if RIGCTLD_PATH:
    print(f"[OK] rigctld found at: {RIGCTLD_PATH}")
else:
    print("[ERROR] rigctld not found in any known location.")
    print("Install Hamlib from https://hamlib.sourceforge.io/")
    sys.exit(1)

# Try to run rigctld with error output
print("\n2. Testing rigctld with COM6 connection...")
print("   (This will show detailed error messages)")
print("-" * 60)

cmd = [
    RIGCTLD_PATH,
    "-m", "3081",
    "-r", "COM6",
    "-s", "19200",
    "-C", "civ_address=0xA2",
    "-t", "4532"
]

print(f"Command: {' '.join(cmd)}\n")

try:
    # Run with stderr captured so we can see errors
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.stdout:
        print("STDOUT:")
        print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    print(f"Exit code: {result.returncode}")

except subprocess.TimeoutExpired:
    print("rigctld started but didn't respond in 5 seconds")
    print("(This might actually be normal - rigctld runs as a daemon)")
except Exception as e:
    print(f"Error running rigctld: {e}")

print("-" * 60)
print("\nTroubleshooting checklist:")
print("  [ ] Radio is powered ON")
print("  [ ] USB cable is connected")
print("  [ ] Verify COM port in Device Manager (Ports > look for ICOM)")
print("  [ ] Radio menu: Connectors > CI-V Baud Rate = 19200")
print("  [ ] Radio menu: Connectors > CI-V Address = A2")
print("  [ ] Radio menu: Connectors > CI-V Echo Back = ON")
print("  [ ] No other software using COM6 (WSJT-X, JTDX, etc)")
print("  [ ] Try baud rate 9600 if 19200 doesn't work")
print("\nAfter fixing any issues, run: python test_ic7300.py")
