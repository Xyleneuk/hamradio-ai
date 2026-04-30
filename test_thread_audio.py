import time
import wave
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication
import sys

class AudioTestThread(QThread):
    result = pyqtSignal(str)

    def run(self):
        from audio_handler import AudioHandler
        from tts_handler import TTSHandler
        from gui.setup_wizard import load_config

        config = load_config()
        input_dev  = config.get('input_device', 1)
        output_dev = config.get('output_device', 7)

        self.result.emit(f"Config says: input={input_dev} output={output_dev}")

        audio = AudioHandler(
            input_device=input_dev,
            output_device=output_dev
        )

        self.result.emit(
            f"AudioHandler using: input={audio.input_device} "
            f"output={audio.output_device} "
            f"sd_output={audio.sd_output}"
        )

        # Generate TTS
        tts = TTSHandler()
        tts.speak_to_file(
            'Test transmission from Mike X-ray Zero Mike X-ray Oscar',
            'tx_audio.wav'
        )

        wf = wave.open('tx_audio.wav', 'rb')
        self.result.emit(
            f"WAV file: rate={wf.getframerate()} "
            f"channels={wf.getnchannels()} "
            f"width={wf.getsampwidth()}"
        )
        wf.close()

        self.result.emit("Playing audio now - check radio TX indicator...")
        audio.play('tx_audio.wav')
        self.result.emit("Playback complete")


app    = QApplication(sys.argv)
thread = AudioTestThread()
thread.result.connect(print)
thread.finished.connect(app.quit)
thread.start()
app.exec()