# Ham Radio AI

AI-powered voice interface for ham radio operations with real-time frequency tracking and QSO logging.

## Quick Start

### Windows

**Quick Start (Easiest Method):**

1. Install prerequisites:
   - Python 3.11+ from https://www.python.org/ (check "Add Python to PATH")
   - Git from https://git-scm.com/
   - Hamlib from https://hamlib.sourceforge.io/ (hamlib-w64-4.7.1.exe)
   - Visual Studio C++ Build Tools (https://visualstudio.microsoft.com/visual-cpp-build-tools/ - select "Desktop development with C++")

2. Clone the repo:
```powershell
git clone https://github.com/Xyleneuk/hamradio-ai.git
cd hamradio-ai
```

3. Run the installer (choose one):
```powershell
# Option A: Batch file (simplest)
install.bat

# Option B: PowerShell script
powershell -ExecutionPolicy Bypass -File install.ps1

# Option C: Manual installation
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

4. Run the app:
```powershell
python main.py
```

**On First Run:**
- Setup wizard will ask for COM port, baud rate, and API key
- COM port: Check Device Manager → Ports (COM & LPT)
- Baud rate: Check your radio manual (usually 9600 or 19200)
- API key: Get from https://console.anthropic.com

**Troubleshooting:**
- PyAudio fails: Install Visual Studio C++ Build Tools (required for compilation)
- Radio connection fails: Run as Administrator (needed for COM port access)
- Check logs: `~/hamradio_ai.log` has detailed diagnostics
- Test radio: `python test_rigctld.py COM6 9600`

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
