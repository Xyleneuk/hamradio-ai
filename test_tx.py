from radio_control import RadioControl
from audio_handler import AudioHandler
from tts_handler import TTSHandler
import time

radio = RadioControl()
radio.connect()
tts = TTSHandler()
audio = AudioHandler()

print('Generating test transmission...')
tts.speak_to_file(
    'This is a test transmission from Mike X-ray Zero Mike X-ray Oscar', 
    'tx_audio.wav'
)

print('Keying PTT in 3 seconds...')
time.sleep(3)
radio.set_ptt(1)
time.sleep(0.3)
audio.play('tx_audio.wav')
time.sleep(0.3)
radio.set_ptt(0)
print('Done')

radio.disconnect()
audio.close()