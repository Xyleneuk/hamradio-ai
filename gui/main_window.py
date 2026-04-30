import sys
import os
import wave
import time
import numpy as np
import pyaudio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QGroupBox,
    QStatusBar, QSplitter, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCursor, QAction


class ActivityLog(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont('Courier New', 9))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                border: 1px solid #333;
                padding: 4px;
            }
        """)

    def _write(self, message, colour):
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
        self.setTextColor(QColor(colour))
        self.append(f"[{timestamp}] {message}")
        self.moveCursor(QTextCursor.MoveOperation.End)

    def log_tx(self, message):
        self._write(f"TX: {message}", '#ff6600')

    def log_rx(self, message):
        self._write(f"RX: {message}", '#00aaff')

    def log_info(self, message):
        self._write(f"    {message}", '#aaaaaa')

    def log_success(self, message):
        self._write(f"✅  {message}", '#00ff00')

    def log_error(self, message):
        self._write(f"❌  {message}", '#ff4444')

    def log_warning(self, message):
        self._write(f"⚠️  {message}", '#ffaa00')


class QSOLogWidget(QTextEdit):
    HEADER = (
        f"{'DATE':<9} {'UTC':<6} {'CALLSIGN':<12} {'BAND':<6} "
        f"{'RST S':<7} {'RST R':<7} {'NAME':<12} {'QTH'}"
    )

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont('Courier New', 9))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a2a;
                color: #cccccc;
                border: 1px solid #333;
                padding: 4px;
            }
        """)
        self._write_header()

    def _write_header(self):
        self.setTextColor(QColor('#4488ff'))
        self.append(self.HEADER)
        self.setTextColor(QColor('#333366'))
        self.append('-' * 80)

    def add_qso(self, qso_data):
        from datetime import datetime, timezone
        now      = datetime.now(timezone.utc)
        date_str = now.strftime('%d/%m/%y')
        time_str = now.strftime('%H%MZ')
        self._write_row(
            date_str,
            time_str,
            qso_data.get('callsign', '?'),
            qso_data.get('band', '?'),
            qso_data.get('rst_sent', '59'),
            qso_data.get('rst_rcvd', '59'),
            qso_data.get('name', ''),
            qso_data.get('qth', '')
        )

    def _write_row(self, date, utc, callsign, band, rst_s, rst_r, name, qth):
        self.setTextColor(QColor('#00ff88'))
        self.append(
            f"{date:<9} {utc:<6} {callsign:<12} {band:<6} "
            f"{rst_s:<7} {rst_r:<7} {name:<12} {qth}"
        )
        self.moveCursor(QTextCursor.MoveOperation.End)

    def load_from_adif(self):
        try:
            from adif.adif_logger import load_all_qsos
            qsos = load_all_qsos()
            if not qsos:
                return
            self.setTextColor(QColor('#555555'))
            self.append(f"  --- {len(qsos)} previous QSOs loaded ---")
            for q in qsos:
                raw_date = q.get('date', '')
                try:
                    date_str = (
                        f"{raw_date[6:8]}/"
                        f"{raw_date[4:6]}/"
                        f"{raw_date[2:4]}"
                    )
                except Exception:
                    date_str = raw_date
                time_str = q.get('time', '') + 'Z'
                self._write_row(
                    date_str,
                    time_str,
                    q.get('callsign', '?'),
                    q.get('band', '?'),
                    q.get('rst_sent', '59'),
                    q.get('rst_rcvd', '59'),
                    q.get('name', ''),
                    q.get('qth', '')
                )
            self.setTextColor(QColor('#333366'))
            self.append('-' * 80)
            self.moveCursor(QTextCursor.MoveOperation.End)
        except Exception as e:
            print(f"Could not load ADIF log: {e}")


class RadioWorker(QThread):
    log_tx      = pyqtSignal(str)
    log_rx      = pyqtSignal(str)
    log_info    = pyqtSignal(str)
    log_success = pyqtSignal(str)
    log_error   = pyqtSignal(str)
    log_warning = pyqtSignal(str)
    qso_logged  = pyqtSignal(dict)
    status_msg  = pyqtSignal(str)
    frequency   = pyqtSignal(float)

    def __init__(self, config, personality):
        super().__init__()
        self.config      = config
        self.personality = personality
        self.running     = False
        self.radio       = None

    def run(self):
        self.running = True
        try:
            self._setup_and_run()
        except Exception as e:
            import traceback
            self.log_error.emit(f"Fatal error: {str(e)}")
            self.log_error.emit(traceback.format_exc())
        finally:
            self._emergency_ptt_release()

    def _emergency_ptt_release(self):
        try:
            if self.radio:
                self.radio.set_ptt(0)
                self.log_warning.emit("PTT released - radio back to RX")
        except Exception as e:
            self.log_error.emit(f"CRITICAL: Could not release PTT: {e}")

    def _setup_and_run(self):
        from radio_control import RadioControl
        from audio_handler import AudioHandler
        from tts_handler   import TTSHandler
        from qso_brain     import QSOBrain
        import whisper

        os.environ['ANTHROPIC_API_KEY'] = self.config.get('api_key', '')

        input_dev  = self.config.get('input_device')
        output_dev = self.config.get('output_device')
        self.log_info.emit(
            f"Audio config: input={input_dev} output={output_dev}"
        )

        self.log_info.emit("Loading Whisper speech recognition...")
        transcriber = whisper.load_model('base')

        self.log_info.emit("Connecting to radio...")
        self.radio = RadioControl()
        self.radio.connect()

        audio = AudioHandler(
            input_device=input_dev,
            output_device=output_dev
        )
        self.log_info.emit(
            f"AudioHandler: input={audio.input_device} "
            f"output={audio.output_device} "
            f"sd_output={audio.sd_output}"
        )

        tts   = TTSHandler()
        brain = QSOBrain()

        brain.our_callsign  = self.config.get('callsign', 'NOCALL')
        brain.operator_name = self.config.get('operator_name', '')
        brain.qth           = self.config.get('qth', '')

        threshold      = self.config.get('audio_threshold', 1500)
        listen_timeout = self.config.get('listen_timeout', 15)
        ptt_delay      = self.config.get('ptt_delay', 300) / 1000

        freq     = self.radio.get_frequency()
        freq_mhz = freq / 1e6
        self.frequency.emit(freq_mhz)
        self.status_msg.emit(
            f"Operating on {freq_mhz:.4f} MHz  |  "
            f"Personality: {self.personality}"
        )
        self.log_success.emit("All systems ready!")

        # ------------------------------------------------------------------
        # Helper: refresh frequency
        # ------------------------------------------------------------------
        def refresh_frequency():
            try:
                f = self.radio.get_frequency() / 1e6
                self.frequency.emit(f)
                return f
            except Exception:
                return freq_mhz

        # ------------------------------------------------------------------
        # Helper: transmit - PTT ALWAYS released via finally
        # ------------------------------------------------------------------
        def transmit(text):
            self.log_tx.emit(text)
            try:
                tts.speak_to_file(text, 'tx_audio.wav')
            except Exception as e:
                self.log_error.emit(f"TTS error: {e}")
                return
            try:
                self.radio.set_ptt(1)
                time.sleep(ptt_delay)
                audio.play('tx_audio.wav')
                time.sleep(ptt_delay)
            except Exception as e:
                self.log_error.emit(f"Audio TX error: {e}")
            finally:
                try:
                    self.radio.set_ptt(0)
                except Exception as e:
                    self.log_error.emit(
                        f"CRITICAL: PTT release failed: {e}"
                    )

        # ------------------------------------------------------------------
        # Helper: listen for signal
        # ------------------------------------------------------------------
        def listen_for_signal(timeout):
            start = time.time()
            while time.time() - start < timeout:
                if not self.running:
                    return False
                level = audio.get_audio_level(0.5)
                if level > threshold:
                    return True
            return False

        # ------------------------------------------------------------------
        # Helper: record and transcribe
        # ------------------------------------------------------------------
        def record_and_transcribe():
            p      = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=8000,
                input=True,
                input_device_index=audio.input_device,
                frames_per_buffer=1024
            )
            recording     = []
            silence_count = 0
            frames_above  = 0
            silence_limit = int(8000 / 1024 * 2)
            max_chunks    = int(8000 / 1024 * 30)

            for _ in range(max_chunks):
                if not self.running:
                    break
                data  = stream.read(1024, exception_on_overflow=False)
                recording.append(data)
                level = np.abs(
                    np.frombuffer(data, dtype=np.int16)
                ).mean()
                if level > threshold:
                    frames_above  += 1
                    silence_count  = 0
                else:
                    silence_count += 1
                    if silence_count > silence_limit and frames_above > 10:
                        break

            stream.stop_stream()
            stream.close()
            p.terminate()

            wf = wave.open('rx_audio.wav', 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(b''.join(recording))
            wf.close()

            result = transcriber.transcribe(
                'rx_audio.wav', language='en', fp16=False
            )
            text = result['text'].strip()
            self.log_rx.emit(text)
            return text

        # ------------------------------------------------------------------
        # Helper: finish and log a QSO
        # ------------------------------------------------------------------
        def finish_qso(current_freq_mhz):
            qso = brain.qso_data.copy()
            qso['band']      = brain._get_band(current_freq_mhz)
            qso['frequency'] = current_freq_mhz
            if qso.get('callsign'):
                self.qso_logged.emit(qso)
                self.log_success.emit(
                    f"QSO logged: {qso['callsign']}  "
                    f"RST {qso.get('rst_sent','?')}/"
                    f"{qso.get('rst_rcvd','?')}"
                )
            else:
                self.log_warning.emit(
                    "QSO ended but no callsign captured - not logged"
                )

        # ------------------------------------------------------------------
        # Run selected personality
        # ------------------------------------------------------------------
        if self.personality == 'General QSO':
            self._run_general_qso(
                brain, transmit, listen_for_signal,
                record_and_transcribe, finish_qso,
                refresh_frequency, freq_mhz, listen_timeout
            )
        elif self.personality == 'Contest':
            self._run_contest(
                brain, transmit, listen_for_signal,
                record_and_transcribe, finish_qso,
                refresh_frequency, freq_mhz, listen_timeout
            )
        elif self.personality == 'Repeater':
            self._run_repeater(
                brain, transmit, listen_for_signal,
                record_and_transcribe,
                refresh_frequency, freq_mhz, listen_timeout
            )

        self.radio.disconnect()
        audio.close()

    # ------------------------------------------------------------------
    # General QSO personality
    # ------------------------------------------------------------------
    def _run_general_qso(
        self, brain, transmit, listen_for_signal,
        record_and_transcribe, finish_qso,
        refresh_frequency, freq_mhz, listen_timeout
    ):
        cq_attempts = 0

        while self.running:
            freq_mhz = refresh_frequency()
            brain.reset()
            self.log_info.emit("Generating CQ call...")
            result = brain.get_cq_call(freq_mhz)
            transmit(result['speech'])
            cq_attempts += 1

            if listen_for_signal(listen_timeout):
                heard = record_and_transcribe()
                if heard:
                    response = brain.process_received_transmission(heard)

                    while (self.running and
                           response['action'] != 'log_and_end'):
                        transmit(response['speech'])
                        if listen_for_signal(listen_timeout):
                            heard    = record_and_transcribe()
                            response = brain.process_received_transmission(
                                heard
                            )
                        else:
                            self.log_warning.emit("No reply - ending QSO")
                            break

                    if response['action'] == 'log_and_end':
                        transmit(response['speech'])

                    freq_mhz = refresh_frequency()
                    finish_qso(freq_mhz)
                    cq_attempts = 0
            else:
                self.log_info.emit(f"No reply to CQ ({cq_attempts}/3)")
                if cq_attempts >= 3:
                    self.log_info.emit("No responses - pausing 60 seconds")
                    for _ in range(60):
                        if not self.running:
                            break
                        time.sleep(1)
                    cq_attempts = 0

    # ------------------------------------------------------------------
    # Contest personality
    # ------------------------------------------------------------------
    def _run_contest(
        self, brain, transmit, listen_for_signal,
        record_and_transcribe, finish_qso,
        refresh_frequency, freq_mhz, listen_timeout
    ):
        serial       = 1
        contest_name = self.config.get('contest_name', 'Contest')
        cq_attempts  = 0
        self.log_info.emit(f"Contest mode: {contest_name}")

        while self.running:
            freq_mhz = refresh_frequency()
            brain.reset()
            cq_text = (
                f"CQ {contest_name}, "
                f"{brain.our_callsign} {brain.our_callsign}"
            )
            transmit(cq_text)
            cq_attempts += 1

            if listen_for_signal(listen_timeout):
                heard = record_and_transcribe()
                if heard:
                    response = brain.process_contest_exchange(heard, serial)
                    transmit(response['speech'])

                    if listen_for_signal(listen_timeout):
                        heard    = record_and_transcribe()
                        response = brain.process_contest_exchange(
                            heard, serial
                        )
                        freq_mhz = refresh_frequency()
                        qso = brain.qso_data.copy()
                        qso['band']        = brain._get_band(freq_mhz)
                        qso['frequency']   = freq_mhz
                        qso['serial_sent'] = str(serial)
                        serial += 1
                        if qso.get('callsign'):
                            self.qso_logged.emit(qso)
                            self.log_success.emit(
                                f"Contest QSO #{serial-1}: "
                                f"{qso['callsign']}  "
                                f"Serial: {qso['serial_sent']} / "
                                f"{qso.get('serial_rcvd','?')}"
                            )
                    cq_attempts = 0
            else:
                if cq_attempts >= 5:
                    self.log_info.emit("No responses - pausing 30 seconds")
                    for _ in range(30):
                        if not self.running:
                            break
                        time.sleep(1)
                    cq_attempts = 0

    # ------------------------------------------------------------------
    # Repeater / info node personality
    # ------------------------------------------------------------------
    def _run_repeater(
        self, brain, transmit, listen_for_signal,
        record_and_transcribe, refresh_frequency,
        freq_mhz, listen_timeout
    ):
        from utils import get_utc_time, get_local_time

        callsign        = self.config.get(
            'repeater_callsign',
            self.config.get('callsign', 'NOCALL')
        )
        # Fixed 60 minute beacon interval
        beacon_interval = 60 * 60
        last_beacon     = 0

        self.log_info.emit(
            f"Repeater mode: {callsign} - beacon every 60 minutes"
        )

        while self.running:
            now = time.time()

            # Hourly beacon - callsign and time only
            if now - last_beacon >= beacon_interval:
                freq_mhz   = refresh_frequency()
                utc_time   = get_utc_time()
                local_time = get_local_time()
                beacon     = (
                    f"{callsign}. "
                    f"{local_time['spoken']}, "
                    f"{utc_time['spoken']}. "
                    f"{callsign}"
                )
                transmit(beacon)
                last_beacon = now
                self.log_info.emit(
                    f"Beacon sent: {callsign} - "
                    f"{utc_time['time_utc']}Z"
                )

            # Listen for queries
            if listen_for_signal(5):
                heard = record_and_transcribe()
                if heard:
                    response     = brain.process_repeater_query(
                        heard, callsign
                    )
                    speech       = response.get('speech', '')
                    caller       = response.get('callsign')
                    request_type = response.get('request_type', 'unknown')

                    if speech:
                        transmit(speech)

                    # Log the contact
                    try:
                        from adif.repeater_logger import log_repeater_contact
                        log_repeater_contact(
                            caller or 'UNKNOWN',
                            request_type,
                            heard,
                            self.config
                        )
                        self.log_success.emit(
                            f"Repeater contact: "
                            f"{caller or 'unknown'} - {request_type}"
                        )
                    except Exception as e:
                        self.log_error.emit(f"Repeater log error: {e}")

            time.sleep(0.5)

    def stop(self):
        self.running = False


# ----------------------------------------------------------------------
# Main application window
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):

    def __init__(self, config, hamlib=None):
        super().__init__()
        self.config  = config
        self.hamlib  = hamlib
        self.worker  = None

        self.setWindowTitle(
            f"Ham Radio AI  —  "
            f"{self.config.get('callsign','NOCALL')}  |  "
            f"{self.config.get('operator_name','')}  |  "
            f"{self.config.get('qth','')}"
        )
        self.setMinimumSize(960, 720)

        self._build_menu()
        self._build_ui()
        self._build_status_bar()

        self.qso_log.load_from_adif()

        self.freq_timer = QTimer()
        self.freq_timer.timeout.connect(self._poll_frequency)
        self.freq_timer.start(5000)

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu     = menubar.addMenu('File')
        wizard_action = QAction('Run Setup Wizard', self)
        wizard_action.triggered.connect(self._run_setup_wizard)
        file_menu.addAction(wizard_action)
        file_menu.addSeparator()
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        radio_menu     = menubar.addMenu('Radio')
        restart_action = QAction('Restart rigctld', self)
        restart_action.triggered.connect(self._restart_rigctld)
        radio_menu.addAction(restart_action)

        help_menu    = menubar.addMenu('Help')
        about_action = QAction('About', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        ctrl_group  = QGroupBox("Control")
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(12)

        ctrl_layout.addWidget(QLabel("Personality:"))
        self.personality_combo = QComboBox()
        self.personality_combo.setMinimumWidth(140)
        personalities = []
        if self.config.get('enable_general', True):
            personalities.append('General QSO')
        if self.config.get('enable_contest', False):
            personalities.append('Contest')
        if self.config.get('enable_repeater', False):
            personalities.append('Repeater')
        if not personalities:
            personalities = ['General QSO']
        self.personality_combo.addItems(personalities)
        ctrl_layout.addWidget(self.personality_combo)

        ctrl_layout.addStretch()

        self.freq_label = QLabel("--- MHz")
        self.freq_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; "
            "color: #00aaff; font-family: 'Courier New'; "
            "padding: 0 16px;"
        )
        ctrl_layout.addWidget(self.freq_label)

        self.radio_indicator = QLabel("●")
        self.radio_indicator.setStyleSheet(
            "color: #ff4444; font-size: 18px;"
        )
        self.radio_indicator.setToolTip("Radio connection status")
        ctrl_layout.addWidget(self.radio_indicator)

        ctrl_layout.addStretch()

        self.start_btn = QPushButton("▶   Start Operating")
        self.start_btn.setMinimumHeight(42)
        self.start_btn.setMinimumWidth(180)
        self._style_btn_start()
        self.start_btn.clicked.connect(self._toggle_operation)
        ctrl_layout.addWidget(self.start_btn)

        ctrl_group.setLayout(ctrl_layout)
        root.addWidget(ctrl_group)

        splitter = QSplitter(Qt.Orientation.Vertical)

        log_group  = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        self.activity_log = ActivityLog()
        self.activity_log.log_info(
            f"Ham Radio AI ready  —  "
            f"{self.config.get('callsign','NOCALL')}  "
            f"{self.config.get('operator_name','')}  "
            f"{self.config.get('qth','')}"
        )
        log_layout.addWidget(self.activity_log)
        log_group.setLayout(log_layout)
        splitter.addWidget(log_group)

        qso_group  = QGroupBox("QSO Log")
        qso_layout = QVBoxLayout()
        self.qso_log = QSOLogWidget()
        qso_layout.addWidget(self.qso_log)
        qso_group.setLayout(qso_layout)
        splitter.addWidget(qso_group)

        splitter.setSizes([450, 220])
        root.addWidget(splitter)

    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "Ready  —  Press Start to begin operating"
        )

    def _style_btn_start(self):
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d7a2d;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover   { background-color: #3d9a3d; }
            QPushButton:pressed { background-color: #1d5a1d; }
        """)

    def _style_btn_stop(self):
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #7a2d2d;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover   { background-color: #9a3d3d; }
            QPushButton:pressed { background-color: #5a1d1d; }
        """)

    def _toggle_operation(self):
        if self.worker and self.worker.isRunning():
            self._stop_operation()
        else:
            self._start_operation()

    def _start_operation(self):
        personality = self.personality_combo.currentText()
        self.worker = RadioWorker(self.config, personality)

        self.worker.log_tx.connect(self.activity_log.log_tx)
        self.worker.log_rx.connect(self.activity_log.log_rx)
        self.worker.log_info.connect(self.activity_log.log_info)
        self.worker.log_success.connect(self.activity_log.log_success)
        self.worker.log_error.connect(self.activity_log.log_error)
        self.worker.log_warning.connect(self.activity_log.log_warning)
        self.worker.qso_logged.connect(self._handle_qso_logged)
        self.worker.status_msg.connect(self.status_bar.showMessage)
        self.worker.frequency.connect(
            lambda f: self.freq_label.setText(f"{f:.4f} MHz")
        )
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

        self.start_btn.setText("⏹   Stop Operating")
        self._style_btn_stop()
        self.personality_combo.setEnabled(False)
        self.radio_indicator.setStyleSheet(
            "color: #00ff00; font-size: 18px;"
        )

    def _stop_operation(self):
        if self.worker:
            self.activity_log.log_info(
                "Stopping - finishing current task..."
            )
            self.worker.stop()
            self.worker.wait(5000)
        self._on_worker_finished()

    def _on_worker_finished(self):
        self.start_btn.setText("▶   Start Operating")
        self._style_btn_start()
        self.personality_combo.setEnabled(True)
        self.radio_indicator.setStyleSheet(
            "color: #ff4444; font-size: 18px;"
        )
        self.status_bar.showMessage(
            "Stopped  —  Press Start to begin operating"
        )
        self.activity_log.log_info("Operation stopped")

    def _handle_qso_logged(self, qso_data):
        self.qso_log.add_qso(qso_data)
        try:
            from adif.adif_logger import log_qso
            log_qso(qso_data, self.config)
        except Exception as e:
            self.activity_log.log_error(f"ADIF log error: {e}")

    def _poll_frequency(self):
        if self.worker and self.worker.isRunning():
            return
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(('localhost', 4532))
            sock.sendall(b'f\n')
            response = sock.recv(1024).decode().strip()
            sock.close()
            freq_mhz = float(response) / 1e6
            self.freq_label.setText(f"{freq_mhz:.4f} MHz")
            self.radio_indicator.setStyleSheet(
                "color: #00ff00; font-size: 18px;"
            )
        except Exception:
            self.radio_indicator.setStyleSheet(
                "color: #ff4444; font-size: 18px;"
            )

    def _run_setup_wizard(self):
        self._stop_operation()
        from gui.setup_wizard import run_wizard, save_config
        new_config = run_wizard()
        if new_config:
            self.config = new_config
            save_config(new_config)
            self.setWindowTitle(
                f"Ham Radio AI  —  "
                f"{self.config.get('callsign','NOCALL')}  |  "
                f"{self.config.get('operator_name','')}  |  "
                f"{self.config.get('qth','')}"
            )
            self.activity_log.log_success("Configuration updated")

    def _restart_rigctld(self):
        if self.hamlib:
            self.activity_log.log_info("Restarting rigctld...")
            if self.hamlib.restart():
                self.activity_log.log_success(
                    "rigctld restarted successfully"
                )
            else:
                self.activity_log.log_error(
                    "Failed to restart rigctld"
                )

    def _show_about(self):
        QMessageBox.about(
            self,
            "About Ham Radio AI",
            "Ham Radio AI  v1.0\n\n"
            "An AI-powered amateur radio operator\n"
            "Powered by Anthropic Claude\n\n"
            "Designed for the amateur radio community\n\n"
            "© 2026 HamRadioAI"
        )

    def closeEvent(self, event):
        self._stop_operation()
        self.freq_timer.stop()
        event.accept()