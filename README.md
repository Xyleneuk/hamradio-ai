# Ham Radio AI

AI-powered voice interface for ham radio operations with real-time frequency tracking and QSO logging.

## Quick Start

### Windows

**Requirements:**
- Python 3.11 or later
- Git
- Hamlib (for radio control)

**Installation:**

1. Install Python 3.11+ from https://www.python.org/
   - ✅ Check "Add Python to PATH" during installation

2. Install Hamlib from https://hamlib.sourceforge.io/
   - Download: `hamlib-w64-4.7.1.exe` (or later)
   - Run installer, keep default settings

3. Clone and install:
```powershell
git clone https://github.com/Xyleneuk/hamradio-ai.git
cd hamradio-ai
pip install -r requirements.txt
```

4. Run:
```powershell
python main.py
```

On first run, the setup wizard will ask for:
- COM port (check Device Manager for your radio)
- Baud rate (usually 9600 or 19200)
- Anthropic API key (get one at https://console.anthropic.com)

**Troubleshooting:**
- Check `~/hamradio_ai.log` for detailed diagnostics
- Run as Administrator if radio connection fails (needed for COM port access)
- Test radio with: `python test_rigctld.py COM6 9600` (adjust port/baud)

---

### Linux

**Requirements:**
- Python 3.11 or later
- Git
- Hamlib development libraries
- Audio libraries (ALSA/PulseAudio)

**Installation (Ubuntu/Debian):**

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip git libhamlib2 libhamlib2-dev libusb-1.0-0 libusb-1.0-0-dev

# Clone and install
git clone https://github.com/Xyleneuk/hamradio-ai.git
cd hamradio-ai
pip install -r requirements.txt

# Run
python main.py
```

**Installation (Fedora/RHEL):**

```bash
# Install dependencies
sudo dnf install -y python3.11 git hamlib hamlib-devel libusb libusb-devel

# Clone and install
git clone https://github.com/Xyleneuk/hamradio-ai.git
cd hamradio-ai
pip install -r requirements.txt

# Run
python main.py
```

**Serial Port Access:**

Add your user to the `dialout` group to access serial ports without sudo:
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

**Troubleshooting:**
- Check `~/hamradio_ai.log` for detailed diagnostics
- Test radio with: `python test_rigctld.py /dev/ttyUSB0 9600` (adjust port/baud)
- Verify rigctld: `rigctld -m 3081 -r /dev/ttyUSB0 -s 9600 -C civ_address=0xA2 -t 4532`

---

## Features

- 🎤 **Voice Control**: Speak callsigns and frequencies using Whisper AI
- 📊 **Real-time Tracking**: Monitor your radio frequency and mode
- 📝 **QSO Logging**: Auto-log contacts with call sign, frequency, signal report
- 🎯 **Setup Wizard**: Easy configuration for your specific radio
- 🔧 **Flexible Radio Support**: Works with any radio supported by Hamlib

## Radio Configuration

On first run, you'll need to configure:
- **COM Port**: Where your radio connects (e.g., COM6, /dev/ttyUSB0)
- **Baud Rate**: Usually 9600 or 19200 (check your radio manual)
- **CI-V Address**: For Icom radios (default 0xA2 for IC-7300)

Find your COM port:
- **Windows**: Device Manager → Ports (COM & LPT)
- **Linux**: `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`

## Development

Clone and set up for development:
```bash
git clone https://github.com/Xyleneuk/hamradio-ai.git
cd hamradio-ai
pip install -r requirements.txt
python main.py
```

## License

(License info here)

## Support

Check `~/hamradio_ai.log` for troubleshooting. Include the log when reporting issues.
