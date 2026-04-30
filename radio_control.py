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
        self.sock.sendall((cmd + '\n').encode())
        time.sleep(0.1)
        response = self.sock.recv(1024).decode().strip()
        return response

    def get_frequency(self):
        response = self.send_command('f')
        return float(response)

    def get_smeter(self):
        response = self.send_command('l STRENGTH')
        return float(response)

    def set_ptt(self, state):
        # 1 = TX, 0 = RX
        self.send_command(f'T {state}')

    def disconnect(self):
        if self.sock:
            self.sock.close()

# Test it
if __name__ == '__main__':
    radio = RadioControl()
    radio.connect()
    
    freq = radio.get_frequency()
    print(f"Frequency: {freq/1e6:.4f} MHz")
    
    smeter = radio.get_smeter()
    print(f"S-Meter: {smeter} dB")
    
    print("Testing PTT - going to TX in 3 seconds...")
    time.sleep(3)
    radio.set_ptt(1)
    print("PTT ON - transmitting!")
    time.sleep(2)
    radio.set_ptt(0)
    print("PTT OFF - back to RX")
    
    radio.disconnect()