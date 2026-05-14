#!/usr/bin/env python3
"""
Simple test script to verify IC-7300 connection via hamlib/rigctld
Run this before launching the GUI to check your radio setup
"""

import sys
import os
import time
from hamlib_manager import HamlibManager
from radio_control import RadioControl

def test_radio_connection():
    """Test IC-7300 connection"""

    # IC-7300 configuration
    config = {
        'radio_model': '3081',      # IC-7300 hamlib model number
        'com_port': 'COM6',         # Change to your COM port
        'baud_rate': '9600',        # Trying slower baud rate
        'civ_address': '0xA2'       # IC-7300 default
    }

    print("=" * 60)
    print("IC-7300 Radio Connection Test")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Radio Model: {config['radio_model']} (IC-7300)")
    print(f"  COM Port: {config['com_port']}")
    print(f"  Baud Rate: {config['baud_rate']}")
    print(f"  CIV Address: {config['civ_address']}")

    # Start rigctld
    print(f"\n1. Starting rigctld daemon...")
    hamlib = HamlibManager(config)

    if not hamlib.start():
        print("[FAILED] rigctld failed to start")
        print("\nTroubleshooting:")
        print("  - Check that your IC-7300 is powered on")
        print("  - Check USB cable is connected")
        print("  - Verify COM port in config (check Device Manager)")
        print("  - Ensure no other software is using the COM port")
        print("  - Try a different baud rate (9600, 38400)")
        return False

    print("[OK] rigctld started successfully")

    # Connect to radio via RadioControl
    print("\n2. Connecting to radio via RadioControl...")
    radio = RadioControl()

    try:
        radio.connect()
        print("[OK] Connected to rigctld")
    except Exception as e:
        print(f"[FAILED] Could not connect: {e}")
        hamlib.stop()
        return False

    # Test frequency readback
    print("\n3. Reading frequency...")
    try:
        freq_hz = radio.get_frequency()
        freq_mhz = freq_hz / 1e6
        print(f"[OK] Frequency: {freq_mhz:.4f} MHz")
    except Exception as e:
        print(f"[FAILED] Could not read frequency: {e}")
        radio.disconnect()
        hamlib.stop()
        return False

    # Test S-meter
    print("\n4. Reading S-Meter...")
    try:
        smeter = radio.get_smeter()
        print(f"[OK] S-Meter: {smeter} dB")
    except Exception as e:
        print(f"[FAILED] Could not read S-Meter: {e}")
        radio.disconnect()
        hamlib.stop()
        return False

    # Test PTT (optional - only if you want to test transmission)
    print("\n5. PTT Test (optional - press Enter to test, or skip):")
    user_input = input("   Test PTT? (y/n): ").strip().lower()

    if user_input == 'y':
        try:
            print("   Keying PTT in 2 seconds...")
            time.sleep(2)
            radio.set_ptt(1)
            print("   [OK] TX - Radio is transmitting")
            time.sleep(2)
            radio.set_ptt(0)
            print("   [OK] RX - PTT released")
        except Exception as e:
            print(f"   [FAILED] PTT test failed: {e}")

    # Cleanup
    radio.disconnect()
    hamlib.stop()

    print("\n" + "=" * 60)
    print("[SUCCESS] All tests passed - Radio connection is working!")
    print("=" * 60)
    print("\nYou can now run the GUI with: python main.py")
    return True


if __name__ == '__main__':
    success = test_radio_connection()
    sys.exit(0 if success else 1)
