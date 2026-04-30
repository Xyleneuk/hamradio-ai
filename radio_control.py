import socket
import time


class RadioControl:
    def __init__(self, host='localhost', port=4532):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(5)
        print("Connected to rigctld")

    def send_command(self, cmd):
        """Send command to rigctld with automatic reconnect on failure"""
        for attempt in range(3):
            try:
                if self.sock is None:
                    self.connect()
                self.sock.sendall((cmd + '\n').encode())
                time.sleep(0.1)
                response = self.sock.recv(1024).decode().strip()
                return response
            except Exception as e:
                print(f"Radio command failed (attempt {attempt+1}): {e}")
                self.sock = None
                time.sleep(0.5)
        raise Exception(f"Radio command '{cmd}' failed after 3 attempts")

    def get_frequency(self):
        response = self.send_command('f')
        return float(response)

    def get_smeter(self):
        response = self.send_command('l STRENGTH')
        return float(response)

    def set_ptt(self, state):
        """Key or unkey PTT - 1=TX, 0=RX"""
        try:
            self.send_command(f'T {state}')
        except Exception as e:
            print(f"PTT error: {e}")
            # Try to reconnect and release PTT
            if state == 0:
                try:
                    self.connect()
                    self.send_command('T 0')
                    print("PTT released after reconnect")
                except Exception as e2:
                    print(f"CRITICAL: PTT release failed: {e2}")

    def disconnect(self):
        try:
            if self.sock:
                self.set_ptt(0)  # Safety - release PTT on disconnect
                self.sock.close()
                self.sock = None
        except Exception as e:
            print(f"Disconnect error: {e}")


# Test
if __name__ == '__main__':
    radio = RadioControl()
    radio.connect()
    freq = radio.get_frequency()
    print(f"Frequency: {freq/1e6:.4f} MHz")
    smeter = radio.get_smeter()
    print(f"S-Meter: {smeter} dB")
    print("PTT test in 2 seconds...")
    time.sleep(2)
    radio.set_ptt(1)
    print("TX")
    time.sleep(2)
    radio.set_ptt(0)
    print("RX")
    radio.disconnect()