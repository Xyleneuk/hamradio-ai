import sys
import json
import os
import logging
import pyaudio
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QCheckBox,
    QGroupBox, QFormLayout, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Try multiple config locations in order of preference
def _get_config_file():
    """Determine config file location with fallbacks"""
    # First try: ~/.hamradio_ai/
    primary = os.path.join(os.path.expanduser('~'), '.hamradio_ai', 'config.json')

    # Fallback: AppData/Local (Windows standard)
    try:
        appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
        secondary = os.path.join(appdata, 'HamRadioAI', 'config.json')
    except:
        secondary = None

    # Fallback: AppData/Local/Roaming
    try:
        localappdata = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
        tertiary = os.path.join(localappdata, 'HamRadioAI', 'config.json')
    except:
        tertiary = None

    return primary, secondary, tertiary

CONFIG_FILE = _get_config_file()[0]  # Default to primary


def save_config(config):
    """Save configuration to file with fallback locations"""
    primary, secondary, tertiary = _get_config_file()
    locations_to_try = [primary, secondary, tertiary]

    for config_file in locations_to_try:
        if not config_file:
            continue

        config_dir = os.path.dirname(config_file)
        logging.info(f"Attempting to save config to: {config_file}")

        try:
            os.makedirs(config_dir, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logging.info(f"Config saved successfully to {config_file}")
            return config_file
        except PermissionError as e:
            logging.warning(f"Permission denied for {config_file}: {e}")
            continue
        except Exception as e:
            logging.warning(f"Failed to save to {config_file}: {e}")
            continue

    # If all locations failed, raise error with all details
    error_msg = f"Failed to save config to any location:\n"
    for loc in locations_to_try:
        if loc:
            error_msg += f"  • {loc}\n"
    logging.error(error_msg)
    raise RuntimeError(error_msg)


def load_config():
    """Load configuration from file, checking all possible locations"""
    primary, secondary, tertiary = _get_config_file()
    locations_to_check = [primary, secondary, tertiary]

    for config_file in locations_to_check:
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    logging.info(f"Loaded config from: {config_file}")
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load config from {config_file}: {e}")
                continue

    logging.debug("No config file found in any location")
    return None


# ----------------------------------------------------------------------
# Page 1 - Welcome
# ----------------------------------------------------------------------
class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Ham Radio AI")
        self.setSubTitle(
            "This wizard will guide you through setting up your AI "
            "radio operator. Please have your radio connected and "
            "powered on before continuing."
        )
        layout = QVBoxLayout()
        info = QLabel(
            "Ham Radio AI is an intelligent radio operator that can:\n\n"
            "  •  Call CQ and conduct general SSB QSOs\n"
            "  •  Operate as a contest station with serial number exchange\n"
            "  •  Run as an information repeater with weather and time\n\n"
            "You will need:\n\n"
            "  •  An Anthropic API key (from console.anthropic.com)\n"
            "  •  Your radio connected via USB\n"
            "  •  Your amateur radio licence callsign\n\n"
            "This setup takes approximately 5 minutes."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 11px; padding: 20px;")
        layout.addWidget(info)
        self.setLayout(layout)


# ----------------------------------------------------------------------
# Page 2 - Station Details
# ----------------------------------------------------------------------
class StationPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Station Details")
        self.setSubTitle(
            "Enter your station information. "
            "This will be used in QSOs and log entries."
        )
        layout = QFormLayout()

        self.callsign = QLineEdit()
        self.callsign.setPlaceholderText("e.g. MX0MXO")
        self.callsign.setMaxLength(10)

        self.operator_name = QLineEdit()
        self.operator_name.setPlaceholderText("e.g. James")

        self.qth = QLineEdit()
        self.qth.setPlaceholderText("e.g. London Heathrow")

        self.locator = QLineEdit()
        self.locator.setPlaceholderText("e.g. IO91sm")
        self.locator.setMaxLength(6)

        self.repeater_callsign = QLineEdit()
        self.repeater_callsign.setPlaceholderText(
            "e.g. MB7UAA (leave blank if not using repeater)"
        )

        layout.addRow("Your Callsign *",     self.callsign)
        layout.addRow("Operator Name *",     self.operator_name)
        layout.addRow("QTH *",               self.qth)
        layout.addRow("Maidenhead Locator",  self.locator)
        layout.addRow("Repeater Callsign",   self.repeater_callsign)

        self.registerField('callsign*',       self.callsign)
        self.registerField('operator_name*',  self.operator_name)
        self.registerField('qth*',            self.qth)

        self.setLayout(layout)

    def get_settings(self):
        return {
            'callsign':           self.callsign.text().upper().strip(),
            'operator_name':      self.operator_name.text().strip(),
            'qth':                self.qth.text().strip(),
            'locator':            self.locator.text().upper().strip(),
            'repeater_callsign':  self.repeater_callsign.text().upper().strip()
        }


# ----------------------------------------------------------------------
# Page 3 - Radio Connection
# ----------------------------------------------------------------------
class RadioPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Radio Connection")
        self.setSubTitle(
            "Configure the connection to your radio. "
            "Make sure it is plugged in and powered on."
        )
        layout = QVBoxLayout()
        form   = QFormLayout()

        # Map display name -> (hamlib model id, default CIV address)
        self._model_info = {
            "Icom IC-9700 (3081)":    ("3081", "0xA2"),
            "Icom IC-7300 (3073)":    ("3073", "0x94"),
            "Icom IC-7100 (3063)":    ("3063", "0x88"),
            "Icom IC-705  (3085)":    ("3085", "0xA4"),
            "Yaesu FT-991A (1045)":   ("1045", ""),
            "Kenwood TS-590S (229)":  ("229",  ""),
        }

        self.radio_model = QComboBox()
        self.radio_model.addItems(list(self._model_info.keys()))
        self.radio_model.currentTextChanged.connect(self._on_model_changed)
        form.addRow("Radio Model", self.radio_model)

        port_layout = QHBoxLayout()
        self.com_port = QComboBox()
        self.com_port.setEditable(True)
        self._refresh_ports()
        port_layout.addWidget(self.com_port)
        refresh_port_btn = QPushButton("Refresh")
        refresh_port_btn.setMaximumWidth(80)
        refresh_port_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(refresh_port_btn)
        form.addRow("CAT COM Port", port_layout)

        self.baud_rate = QComboBox()
        self.baud_rate.addItems([
            '4800', '9600', '19200', '38400', '57600', '115200'
        ])
        self.baud_rate.setCurrentText('19200')
        form.addRow("Baud Rate", self.baud_rate)

        self.civ_address = QLineEdit()
        self.civ_address.setPlaceholderText("e.g. 0x94 for IC-7300")
        form.addRow("CI-V Address", self.civ_address)

        # Set defaults for the initial selection
        self._on_model_changed(self.radio_model.currentText())

        layout.addLayout(form)

        test_btn = QPushButton("Test Radio Connection")
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _on_model_changed(self, text):
        _, civ = self._model_info.get(text, ("", ""))
        self.civ_address.setText(civ)
        self.civ_address.setEnabled(bool(civ))

    def _refresh_ports(self):
        self.com_port.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.com_port.addItem(
                f"{port.device} - {port.description}",
                port.device
            )
        if self.com_port.count() == 0:
            self.com_port.addItem("No ports found")

    def _test_connection(self):
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(('localhost', 4532))
            sock.sendall(b'f\n')
            response = sock.recv(1024).decode().strip()
            sock.close()
            freq = float(response) / 1e6
            self.status_label.setText(
                f"✅ Connected! Frequency: {freq:.4f} MHz"
            )
            self.status_label.setStyleSheet(
                "color: green; font-weight: bold;"
            )
        except Exception:
            self.status_label.setText(
                "❌ Connection failed - is rigctld running?"
            )
            self.status_label.setStyleSheet(
                "color: red; font-weight: bold;"
            )

    def _get_model_number(self):
        model_id, _ = self._model_info.get(self.radio_model.currentText(), ("3081", ""))
        return model_id

    def get_settings(self):
        port_data = self.com_port.currentData()
        return {
            'radio_model': self._get_model_number(),
            'com_port':    port_data or self.com_port.currentText().split(' - ')[0],
            'baud_rate':   self.baud_rate.currentText(),
            'civ_address': self.civ_address.text().strip()
        }


# ----------------------------------------------------------------------
# Page 4 - Audio Devices
# ----------------------------------------------------------------------
class AudioPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Audio Devices")
        self.setSubTitle(
            "Select the audio devices for your radio. "
            "Only devices that work correctly are shown."
        )
        layout = QVBoxLayout()
        form   = QFormLayout()

        self.input_device  = QComboBox()
        self.output_device = QComboBox()

        form.addRow("Radio RX (Input)",  self.input_device)
        form.addRow("Radio TX (Output)", self.output_device)
        layout.addLayout(form)

        # Populate with tested devices
        self._populate_audio_devices()

        refresh_btn = QPushButton("Re-scan Audio Devices")
        refresh_btn.clicked.connect(self._populate_audio_devices)
        layout.addWidget(refresh_btn)

        # Signal detection threshold
        threshold_group  = QGroupBox("Signal Detection")
        threshold_layout = QFormLayout()
        self.threshold   = QSpinBox()
        self.threshold.setRange(100, 10000)
        self.threshold.setValue(1500)
        self.threshold.setSuffix("  (audio level units)")
        threshold_layout.addRow("Detection Threshold", self.threshold)

        hint = QLabel(
            "Set this just above your noise floor. "
            "Run the level monitor after setup to calibrate."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 10px;")
        threshold_layout.addRow("", hint)
        threshold_group.setLayout(threshold_layout)
        layout.addWidget(threshold_group)

        # Timing
        timing_group  = QGroupBox("Timing")
        timing_layout = QFormLayout()

        self.listen_timeout = QSpinBox()
        self.listen_timeout.setRange(5, 60)
        self.listen_timeout.setValue(15)
        self.listen_timeout.setSuffix(" seconds")
        timing_layout.addRow("Listen Timeout", self.listen_timeout)

        self.ptt_delay = QSpinBox()
        self.ptt_delay.setRange(100, 1000)
        self.ptt_delay.setValue(300)
        self.ptt_delay.setSuffix(" ms")
        timing_layout.addRow("PTT Delay", self.ptt_delay)

        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)

        self.setLayout(layout)

    def _populate_audio_devices(self):
        """
        Populate device lists with only tested working devices.
        Tests each candidate at 8000Hz before adding it.
        Auto-selects the first working device whose name contains
        a known radio audio keyword.
        """
        self.input_device.clear()
        self.output_device.clear()

        p = pyaudio.PyAudio()

        radio_keywords = [
            'USB Audio CODEC',
            'USB Audio',
            'IC-',
            'FT-',
            'TS-',
            'SDR',
        ]

        first_radio_input  = None
        first_radio_output = None

        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
            except Exception:
                continue

            name = info['name']

            # Test as input
            if info['maxInputChannels'] > 0:
                try:
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=8000,
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=1024
                    )
                    stream.close()
                    label = f"{name}  [device {i}]"
                    self.input_device.addItem(label, i)
                    # Auto select first radio-like device
                    if first_radio_input is None:
                        if any(kw in name for kw in radio_keywords):
                            first_radio_input = self.input_device.count() - 1
                except Exception:
                    pass  # Device doesn't work at 8000Hz - skip it

            # Test as output
            if info['maxOutputChannels'] > 0:
                try:
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=8000,
                        output=True,
                        output_device_index=i,
                        frames_per_buffer=1024
                    )
                    stream.close()
                    label = f"{name}  [device {i}]"
                    self.output_device.addItem(label, i)
                    # Auto select first radio-like device
                    if first_radio_output is None:
                        if any(kw in name for kw in radio_keywords):
                            first_radio_output = self.output_device.count() - 1
                except Exception:
                    pass  # Device doesn't work at 8000Hz - skip it

        p.terminate()

        if first_radio_input is not None:
            self.input_device.setCurrentIndex(first_radio_input)
        if first_radio_output is not None:
            self.output_device.setCurrentIndex(first_radio_output)

    def get_settings(self):
        return {
            'input_device':       self.input_device.currentData(),
            'input_device_name':  self.input_device.currentText(),
            'output_device':      self.output_device.currentData(),
            'output_device_name': self.output_device.currentText(),
            'audio_threshold':    self.threshold.value(),
            'listen_timeout':     self.listen_timeout.value(),
            'ptt_delay':          self.ptt_delay.value()
        }


# ----------------------------------------------------------------------
# Page 5 - Anthropic API Key
# ----------------------------------------------------------------------
class APIPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Anthropic API Key")
        self.setSubTitle(
            "An Anthropic API key is required to power the AI operator. "
            "Get one free at console.anthropic.com"
        )
        layout = QVBoxLayout()
        form   = QFormLayout()

        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("sk-ant-...")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)

        show_key = QCheckBox("Show API key")
        show_key.toggled.connect(
            lambda checked: self.api_key.setEchoMode(
                QLineEdit.EchoMode.Normal if checked
                else QLineEdit.EchoMode.Password
            )
        )

        form.addRow("API Key *", self.api_key)
        form.addRow("",          show_key)
        layout.addLayout(form)

        test_btn = QPushButton("Test API Key")
        test_btn.clicked.connect(self._test_api)
        layout.addWidget(test_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        info = QLabel(
            "Your API key is stored locally on your computer only.\n"
            "It is never shared with anyone other than Anthropic."
        )
        info.setStyleSheet("color: gray; font-size: 10px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        self.registerField('api_key*', self.api_key)
        self.setLayout(layout)

    def _test_api(self):
        try:
            import anthropic
            client   = anthropic.Anthropic(api_key=self.api_key.text())
            response = client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=10,
                messages=[{'role': 'user', 'content': 'Say OK'}]
            )
            self.status_label.setText("✅ API key valid!")
            self.status_label.setStyleSheet(
                "color: green; font-weight: bold;"
            )
        except Exception as e:
            self.status_label.setText(f"❌ Invalid API key: {str(e)[:60]}")
            self.status_label.setStyleSheet(
                "color: red; font-weight: bold;"
            )

    def get_settings(self):
        return {
            'api_key': self.api_key.text().strip()
        }


# ----------------------------------------------------------------------
# Page 6 - Personalities
# ----------------------------------------------------------------------
class PersonalityPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Personalities")
        self.setSubTitle(
            "Select which AI personalities to enable. "
            "You can change these at any time from the main application."
        )
        layout = QVBoxLayout()

        # General QSO
        general_group  = QGroupBox("General QSO Operator")
        general_layout = QVBoxLayout()
        self.enable_general = QCheckBox("Enable General QSO personality")
        self.enable_general.setChecked(True)
        general_desc = QLabel(
            "Conducts standard SSB QSOs. Exchanges callsigns, RST reports, "
            "name and QTH. Logs full ADIF records."
        )
        general_desc.setWordWrap(True)
        general_desc.setStyleSheet("color: gray; font-size: 10px;")
        general_layout.addWidget(self.enable_general)
        general_layout.addWidget(general_desc)
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Contest
        contest_group  = QGroupBox("Contest Operator")
        contest_layout = QVBoxLayout()
        self.enable_contest = QCheckBox("Enable Contest personality")
        contest_desc = QLabel(
            "Fast-paced contest operation. Exchanges RST and sequential "
            "serial numbers. Optimised for speed and accuracy."
        )
        contest_desc.setWordWrap(True)
        contest_desc.setStyleSheet("color: gray; font-size: 10px;")
        contest_form = QFormLayout()
        self.contest_name = QLineEdit()
        self.contest_name.setPlaceholderText(
            "e.g. RSGB ROPOCO, CQ WW SSB"
        )
        contest_form.addRow("Contest Name:", self.contest_name)
        contest_layout.addWidget(self.enable_contest)
        contest_layout.addWidget(contest_desc)
        contest_layout.addLayout(contest_form)
        contest_group.setLayout(contest_layout)
        layout.addWidget(contest_group)

        # Repeater
        repeater_group  = QGroupBox("Repeater / Info Node")
        repeater_layout = QVBoxLayout()
        self.enable_repeater = QCheckBox("Enable Repeater personality")
        repeater_desc = QLabel(
            "Provides time, weather, traffic and news information. "
            "Beacons callsign at regular intervals. No QSO logging."
        )
        repeater_desc.setWordWrap(True)
        repeater_desc.setStyleSheet("color: gray; font-size: 10px;")
        repeater_form = QFormLayout()
        self.beacon_interval = QSpinBox()
        self.beacon_interval.setRange(10, 60)
        self.beacon_interval.setValue(30)
        self.beacon_interval.setSuffix(" minutes")
        repeater_form.addRow("Beacon Interval:", self.beacon_interval)
        repeater_layout.addWidget(self.enable_repeater)
        repeater_layout.addWidget(repeater_desc)
        repeater_layout.addLayout(repeater_form)
        repeater_group.setLayout(repeater_layout)
        layout.addWidget(repeater_group)

        self.setLayout(layout)

    def get_settings(self):
        return {
            'enable_general':  self.enable_general.isChecked(),
            'enable_contest':  self.enable_contest.isChecked(),
            'enable_repeater': self.enable_repeater.isChecked(),
            'contest_name':    self.contest_name.text().strip(),
            'beacon_interval': self.beacon_interval.value()
        }


# ----------------------------------------------------------------------
# Page 7 - Finish
# ----------------------------------------------------------------------
class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle(
            "Your Ham Radio AI is ready. "
            "Click Save & Launch to start the application."
        )
        layout = QVBoxLayout()
        info   = QLabel(
            "Before transmitting please ensure:\n\n"
            "  ✅  You hold a valid amateur radio licence\n"
            "  ✅  Your callsign is correct\n"
            "  ✅  You are operating within your licence conditions\n"
            "  ✅  A licensed operator is present at all times\n\n"
            f"Your settings will be saved to:\n{CONFIG_FILE}\n\n"
            "You can re-run this wizard at any time from the Settings menu."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 11px; padding: 20px;")
        layout.addWidget(info)
        self.setLayout(layout)


# ----------------------------------------------------------------------
# Wizard
# ----------------------------------------------------------------------
class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ham Radio AI - Setup Wizard")
        self.setMinimumWidth(620)
        self.setMinimumHeight(520)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.addPage(WelcomePage())
        self.addPage(StationPage())
        self.addPage(RadioPage())
        self.addPage(AudioPage())
        self.addPage(APIPage())
        self.addPage(PersonalityPage())
        self.addPage(FinishPage())

        self.setButtonText(
            QWizard.WizardButton.FinishButton, 'Save & Launch'
        )

    def get_config(self):
        """Collect all settings from all pages"""
        config = {}
        for page_id in self.pageIds():
            page = self.page(page_id)
            if hasattr(page, 'get_settings'):
                config.update(page.get_settings())
        return config


# ----------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------
def run_wizard(parent=None):
    """Run the setup wizard and return config if accepted"""
    wizard = SetupWizard(parent)
    if wizard.exec() == QWizard.DialogCode.Accepted:
        config = wizard.get_config()
        save_config(config)
        return config
    return None


# ----------------------------------------------------------------------
# Test
# ----------------------------------------------------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    config = run_wizard()
    if config:
        print("\nConfiguration saved:")
        print(json.dumps(config, indent=2))