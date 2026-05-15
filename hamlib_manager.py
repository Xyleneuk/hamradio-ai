import subprocess
import socket
import time
import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

if getattr(sys, 'frozen', False):
    # When running as a PyInstaller exe, use the extraction directory
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Try bundled version first, then system-wide installation
BUNDLED_RIGCTLD = os.path.join(BASE_DIR, 'hamlib', 'bin', 'rigctld.exe')
SYSTEM_RIGCTLD = r'C:\Program Files\hamlib-w64-4.7.1\bin\rigctld.exe'

RIGCTLD_PATH = BUNDLED_RIGCTLD if os.path.exists(BUNDLED_RIGCTLD) else SYSTEM_RIGCTLD
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
            logging.debug(f"rigctld is responding: {response.decode().strip()}")
            return True
        except socket.timeout:
            logging.debug(f"Connection timeout to port {RIGCTLD_PORT}")
            return False
        except ConnectionRefusedError:
            logging.debug(f"Connection refused on port {RIGCTLD_PORT}")
            return False
        except Exception as e:
            logging.debug(f"Error checking rigctld: {e}")
            return False

    def start(self):
        """Start rigctld as a background process"""
        logging.info("=== Starting rigctld ===")

        if self.is_running():
            logging.info("rigctld already running on port 4532")
            return True

        logging.debug(f"Checking for rigctld executable...")
        logging.debug(f"  Bundled: {BUNDLED_RIGCTLD} (exists: {os.path.exists(BUNDLED_RIGCTLD)})")
        logging.debug(f"  System: {SYSTEM_RIGCTLD} (exists: {os.path.exists(SYSTEM_RIGCTLD)})")
        logging.debug(f"  Using: {RIGCTLD_PATH}")

        if not os.path.exists(RIGCTLD_PATH):
            logging.error(f"rigctld not found at {RIGCTLD_PATH}")
            logging.error(f"Checked bundled: {BUNDLED_RIGCTLD}")
            logging.error(f"Checked system: {SYSTEM_RIGCTLD}")
            logging.error(f"Install hamlib from: https://hamlib.sourceforge.io/")
            return False

        model       = self.config.get('radio_model', '3081')
        com_port    = self.config.get('com_port', 'COM5')
        baud_rate   = self.config.get('baud_rate', '19200')
        civ_address = self.config.get('civ_address', '')

        cmd = [
            RIGCTLD_PATH,
            '-m', model,
            '-r', com_port,
            '-s', baud_rate,
            '-t', str(RIGCTLD_PORT)
        ]
        if civ_address:
            cmd += ['-C', f'civaddr={civ_address}']

        logging.info(f"Command: {' '.join(cmd)}")
        logging.info(f"Radio config: model={model}, port={com_port}, baud={baud_rate}, civ={civ_address}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            logging.info(f"rigctld process started (PID: {self.process.pid})")
        except Exception as e:
            logging.error(f"Failed to start rigctld: {e}", exc_info=True)
            return False

        # Wait up to 30 seconds for rigctld to be ready
        logging.info("Waiting for rigctld to initialise...")
        for i in range(60):
            time.sleep(0.5)

            # Check if process crashed
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                logging.error(f"rigctld exited with code {self.process.returncode}")
                if stdout:
                    logging.error(f"stdout: {stdout.decode()}")
                if stderr:
                    logging.error(f"stderr: {stderr.decode()}")
                return False

            if self.is_running():
                logging.info(f"rigctld ready after {(i+1)*0.5:.1f}s")
                return True

            if i % 4 == 0:
                logging.debug(f"Still waiting... {i*0.5:.1f}s")

        logging.error("rigctld failed to start in time (timeout after 30s)")
        if self.process:
            self.process.terminate()
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