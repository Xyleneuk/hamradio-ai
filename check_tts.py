import wave
from tts_handler import TTSHandler

tts = TTSHandler()
tts.speak_to_file('test transmission', 'tx_audio.wav')

wf = wave.open('tx_audio.wav', 'rb')
print(f'Channels:    {wf.getnchannels()}')
print(f'Sample rate: {wf.getframerate()}')
print(f'Sample width:{wf.getsampwidth()}')
wf.close()