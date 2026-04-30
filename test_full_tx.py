import wave
import pyaudio
import time
import socket
from tts_handler import TTSHandler
from radio_control import RadioControl

CHUNK = 1024

def send_ptt(state):
    """Direct PTT via socket"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('localhost', 4532))
        sock.sendall(f'T {state}\n'.encode())
        sock.recv(1024)
        sock.close()
        print(f"PTT {'ON' if state else 'OFF'}")
    except Exception as e:
        print(f"PTT error: {e}")

# Step 1 - Generate TTS
print("Step 1: Generating TTS...")
tts = TTSHandler()
tts.speak_to_file(
    'CQ CQ CQ this is Mike X-ray Zero Mike X-ray Oscar calling CQ and standing by',
    'tx_audio.wav'
)

wf = wave.open('tx_audio.wav', 'rb')
rate     = wf.getframerate()
channels = wf.getnchannels()
width    = wf.getsampwidth()
wf.close()
print(f"WAV: rate={rate} channels={channels} width={width}")

# Step 2 - Key PTT
print("\nStep 2: Keying PTT in 3 seconds...")
time.sleep(3)
send_ptt(1)
time.sleep(0.3)

# Step 3 - Play audio
print("\nStep 3: Playing audio to radio...")
try:
    p  = pyaudio.PyAudio()
    wf = wave.open('tx_audio.wav', 'rb')

    stream = p.open(
        format=p.get_format_from_width(wf.getsampwidth()),
        channels=wf.getnchannels(),
        rate=wf.getframerate(),
        output=True,
        output_device_index=7,
        frames_per_buffer=CHUNK
    )

    data = wf.readframes(CHUNK)
    while data:
        stream.write(data)
        data = wf.readframes(CHUNK)

    stream.stop_stream()
    stream.close()
    wf.close()
    p.terminate()
    print("Audio playback complete")

except Exception as e:
    print(f"Audio error: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Always release PTT
    time.sleep(0.3)
    send_ptt(0)
    print("PTT released")