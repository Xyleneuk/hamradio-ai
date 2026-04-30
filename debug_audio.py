import wave
import pyaudio
import os

CHUNK = 1024

# First generate the TTS file
from tts_handler import TTSHandler
tts = TTSHandler()
tts.speak_to_file('CQ CQ this is Mike X-ray Zero Mike X-ray Oscar', 'tx_audio.wav')

print(f"\ntx_audio.wav exists: {os.path.exists('tx_audio.wav')}")
print(f"tx_audio.wav size:   {os.path.getsize('tx_audio.wav')} bytes")

wf = wave.open('tx_audio.wav', 'rb')
rate     = wf.getframerate()
channels = wf.getnchannels()
width    = wf.getsampwidth()
print(f"\nWAV info: rate={rate} channels={channels} width={width}")
wf.close()

# Try opening device 7 with exact WAV parameters
print("\nTesting device 7...")
p = pyaudio.PyAudio()
info = p.get_device_info_by_index(7)
print(f"Device 7: {info['name']}")
print(f"  maxOutputChannels: {info['maxOutputChannels']}")
print(f"  defaultSampleRate: {info['defaultSampleRate']}")

try:
    wf = wave.open('tx_audio.wav', 'rb')
    fmt = p.get_format_from_width(wf.getsampwidth())
    print(f"\nOpening stream: fmt={fmt} ch={wf.getnchannels()} rate={wf.getframerate()} device=7")
    stream = p.open(
        format=fmt,
        channels=wf.getnchannels(),
        rate=wf.getframerate(),
        output=True,
        output_device_index=7,
        frames_per_buffer=CHUNK
    )
    print("Stream opened OK - playing...")
    data = wf.readframes(CHUNK)
    while data:
        stream.write(data)
        data = wf.readframes(CHUNK)
    stream.stop_stream()
    stream.close()
    wf.close()
    print("Playback complete - did you hear it through the radio?")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()

p.terminate()