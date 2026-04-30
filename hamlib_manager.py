import subprocess
import socket
import time
import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RIGCTLD_PATH = os.path.join(BASE_DIR, 'hamlib', 'bin', 'rigctld.exe')
RIGCTLD_PORT = 4532


class HamlibManager:
    def __init__(self, config):
        self.config  = config
        self.process = None

    def is_running(self):
        """Check if rigctld is responding on port 4532"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(('localhost', RIGCTLD_PORT))
            sock.sendall(b'f\n')
            response = sock.recv(1024)
            sock.close()
            return True
        except Exception:
            return False

    def start(self):
        """Start rigctld as a background process"""
        if self.is_running():
            print("rigctld already running")
            return True

        if not os.path.exists(RIGCTLD_PATH):
            print(f"rigctld not found at {RIGCTLD_PATH}")
            return False

        model       = self.config.get('radio_model', '3081')
        com_port    = self.config.get('com_port', 'COM5')
        baud_rate   = self.config.get('baud_rate', '19200')
        civ_address = self.config.get('civ_address', '0xA2')

        cmd = [
            RIGCTLD_PATH,
            '-m', model,
            '-r', com_port,
            '-s', baud_rate,
            '-C', f'civ_address={civ_address}',
            '-t', str(RIGCTLD_PORT)
        ]

        print(f"Starting rigctld: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # Wait up to 10 seconds for rigctld to be ready
        print("Waiting for rigctld to initialise...")
        for i in range(20):
            time.sleep(0.5)
            if self.is_running():
                print(f"rigctld ready after {(i+1)*0.5:.1f}s")
                return True

        print("rigctld failed to start in time")
        return False

    def stop(self):
        """Stop rigctld"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            print("rigctld stopped")

    def restart(self):
        self.stop()
        time.sleep(1)
        return self.start()


if __name__ == '__main__':
    config = {
        'radio_model': '3081',
        'com_port':    'COM5',
        'baud_rate':   '19200',
        'civ_address': '0xA2'
    }
    manager = HamlibManager(config)
    print("Starting rigctld...")
    if manager.start():
        print("Success!")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 4532))
            sock.sendall(b'f\n')
            freq = float(sock.recv(1024).decode().strip()) / 1e6
            sock.close()
            print(f"Frequency: {freq:.4f} MHz")
        except Exception as e:
            print(f"Test failed: {e}")
        manager.stop()
    else:
        print("Failed")