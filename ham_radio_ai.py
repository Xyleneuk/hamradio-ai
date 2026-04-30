import time
import os
import json
from datetime import datetime, timezone
from radio_control import RadioControl
from audio_handler import AudioHandler
from qso_brain import QSOBrain
from tts_handler import TTSHandler
import whisper

# Configuration
RIGCTLD_HOST = 'localhost'
RIGCTLD_PORT = 4532
INPUT_DEVICE = 1    # USB Audio CODEC - RX from radio
OUTPUT_DEVICE = 7   # USB Audio CODEC - TX to radio
AUDIO_THRESHOLD = 500   # Audio level to detect incoming signal
LISTEN_TIMEOUT = 15     # Seconds to wait for a reply before giving up
CQ_REPEAT = 3           # Number of CQ calls before giving up
ADIF_LOG = 'C:\\hamradio\\qso_log.adi'

class HamRadioAI:
    def __init__(self):
        print("Initialising Ham Radio AI...")
        print("Loading Whisper...")
        self.transcriber = whisper.load_model('base')
        print("Connecting to radio...")
        self.radio = RadioControl(RIGCTLD_HOST, RIGCTLD_PORT)
        self.radio.connect()
        self.audio = AudioHandler()
        self.audio.input_device = INPUT_DEVICE
        self.audio.output_device = OUTPUT_DEVICE
        self.tts = TTSHandler()
        self.brain = QSOBrain()
        print("All systems ready!")

    def transmit(self, text):
        """Convert text to speech and transmit via radio"""
        print(f"\n>>> TRANSMITTING: {text}\n")
        
        # Generate speech file
        self.tts.speak_to_file(text, 'tx_audio.wav')
        
        # Key PTT and play audio
        self.radio.set_ptt(1)
        time.sleep(0.3)  # Small delay after PTT before speaking
        self.audio.play('tx_audio.wav')
        time.sleep(0.3)  # Small delay before releasing PTT
        self.radio.set_ptt(0)
        
        print(">>> PTT released, listening...\n")

    def listen_for_signal(self, timeout=15):
        """Wait for audio activity on the frequency"""
        print(f"Listening for signal (timeout {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            level = self.audio.get_audio_level(0.5)
            print(f"Audio level: {level:.0f}", end='\r')
            
            if level > AUDIO_THRESHOLD:
                print(f"\nSignal detected! Level: {level:.0f}")
                return True
            
        print("\nNo signal detected")
        return False

    def record_transmission(self, max_duration=30):
        """Record incoming transmission until silence"""
        print("Recording transmission...")
        frames_above = 0
        silence_count = 0
        recording = []
        
        import pyaudio
        import numpy as np
        p = pyaudio.PyAudio()
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=8000,
            input=True,
            input_device_index=INPUT_DEVICE,
            frames_per_buffer=1024
        )

        max_chunks = int(8000 / 1024 * max_duration)
        silence_limit = int(8000 / 1024 * 2)  # 2 seconds silence = end of transmission
        
        for _ in range(max_chunks):
            data = stream.read(1024, exception_on_overflow=False)
            recording.append(data)
            level = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
            
            if level > AUDIO_THRESHOLD:
                frames_above += 1
                silence_count = 0
            else:
                silence_count += 1
                if silence_count > silence_limit and frames_above > 10:
                    print("Transmission ended (silence detected)")
                    break

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save recording
        import wave
        wf = wave.open('rx_audio.wav', 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b''.join(recording))
        wf.close()
        
        return 'rx_audio.wav'

    def transcribe(self, audio_file):
        """Transcribe audio to text using Whisper"""
        print("Transcribing...")
        result = self.transcriber.transcribe(
            audio_file,
            language='en',
            fp16=False
        )
        text = result['text'].strip()
        print(f"Heard: {text}")
        return text

    def log_qso(self, qso_data, frequency_mhz):
        """Write QSO to ADIF log file"""
        if not qso_data.get('callsign'):
            print("No callsign - skipping log entry")
            return

        now = datetime.now(timezone.utc)
        date_str = now.strftime('%Y%m%d')
        time_str = now.strftime('%H%M')
        band = self.brain._get_band(frequency_mhz)

        adif_record = (
            f"<CALL:{len(qso_data['callsign'])}>{qso_data['callsign']}"
            f"<QSO_DATE:8>{date_str}"
            f"<TIME_ON:4>{time_str}"
            f"<BAND:{len(band)}>{band}"
            f"<FREQ:{len(str(frequency_mhz))}>{frequency_mhz}"
            f"<MODE:3>SSB"
            f"<RST_SENT:{len(qso_data.get('rst_sent','59'))}>{qso_data.get('rst_sent','59')}"
            f"<RST_RCVD:{len(qso_data.get('rst_rcvd','59'))}>{qso_data.get('rst_rcvd','59')}"
        )

        if qso_data.get('name'):
            adif_record += f"<NAME:{len(qso_data['name'])}>{qso_data['name']}"
        if qso_data.get('qth'):
            adif_record += f"<QTH:{len(qso_data['qth'])}>{qso_data['qth']}"

        adif_record += "<EOR>\n"

        # Write to log file
        with open(ADIF_LOG, 'a') as f:
            f.write(adif_record)

        print(f"\n✅ QSO logged: {qso_data['callsign']} on {band}")
        print(f"   RST sent: {qso_data.get('rst_sent','?')} received: {qso_data.get('rst_rcvd','?')}")
        if qso_data.get('name'):
            print(f"   Name: {qso_data['name']}")
        if qso_data.get('qth'):
            print(f"   QTH: {qso_data['qth']}")

    def run_cq_session(self):
        """Main CQ loop"""
        freq = self.radio.get_frequency()
        freq_mhz = freq / 1e6
        print(f"\nStarting CQ session on {freq_mhz:.4f} MHz")

        cq_attempts = 0

        while True:
            # Generate and send CQ
            self.brain.reset()
            result = self.brain.get_cq_call(freq_mhz)
            self.transmit(result['speech'])
            cq_attempts += 1

            # Listen for reply
            if self.listen_for_signal(timeout=LISTEN_TIMEOUT):
                # Someone replied - record and process
                audio_file = self.record_transmission()
                heard_text = self.transcribe(audio_file)

                if heard_text:
                    # Process through Claude brain
                    response = self.brain.process_received_transmission(heard_text)
                    
                    # Keep going until QSO complete
                    while response['action'] != 'log_and_end':
                        self.transmit(response['speech'])
                        
                        if self.listen_for_signal(timeout=LISTEN_TIMEOUT):
                            audio_file = self.record_transmission()
                            heard_text = self.transcribe(audio_file)
                            response = self.brain.process_received_transmission(heard_text)
                        else:
                            print("No reply received - ending QSO")
                            break

                    # Log the contact
                    self.log_qso(self.brain.qso_data, freq_mhz)
                    cq_attempts = 0

            else:
                print(f"No reply to CQ (attempt {cq_attempts}/{CQ_REPEAT})")
                if cq_attempts >= CQ_REPEAT:
                    print("No responses after 3 CQ calls - waiting 60 seconds")
                    time.sleep(60)
                    cq_attempts = 0

    def close(self):
        self.radio.disconnect()
        self.audio.close()


# Run it
if __name__ == '__main__':
    ai = HamRadioAI()
    
    try:
        print("\nPress Ctrl+C to stop")
        ai.run_cq_session()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        ai.close()