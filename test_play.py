import wave
import pyaudio

CHUNK = 1024

wf = wave.open('tx_audio.wav', 'rb')
print(f'Sample rate: {wf.getframerate()}')
print(f'Channels:    {wf.getnchannels()}')
print(f'Width:       {wf.getsampwidth()}')

p = pyaudio.PyAudio()

# Try device 7 with the WAV file's actual sample rate
try:
    stream = p.open(
        format=p.get_format_from_width(wf.getsampwidth()),
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
    print("Playback complete")
except Exception as e:
    print(f"Failed: {e}")
    print("Trying device 17...")
    wf.rewind()
    try:
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
            output_device_index=17,
            frames_per_buffer=CHUNK
        )
        print("Stream opened OK on device 17 - playing...")
        data = wf.readframes(CHUNK)
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)
        stream.stop_stream()
        stream.close()
        print("Playback complete on device 17")
    except Exception as e2:
        print(f"Device 17 also failed: {e2}")

wf.close()
p.terminate()