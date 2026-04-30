import pyaudio
import wave
import numpy as np
import time

# IC-9700 USB Audio device indices (from our earlier scan)
INPUT_DEVICE = 1   # Microphone (USB Audio CODEC) - RX from radio
OUTPUT_DEVICE = 7  # Speakers (USB Audio CODEC) - TX to radio

SAMPLE_RATE = 8000    # 8kHz is fine for SSB voice
CHUNK = 1024          # Audio buffer size
FORMAT = pyaudio.paInt16
CHANNELS = 1          # Mono

class AudioHandler:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_device = INPUT_DEVICE
        self.output_device = OUTPUT_DEVICE

    def record(self, duration, filename='rx_audio.wav'):
        """Record audio from radio RX"""
        print(f"Recording {duration} seconds from radio...")
        
        stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.input_device,
            frames_per_buffer=CHUNK
        )

        frames = []
        for _ in range(int(SAMPLE_RATE / CHUNK * duration)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        # Save to WAV file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        print(f"Saved to {filename}")
        return filename

    def play(self, filename):
        """Play audio file to radio TX"""
        print(f"Playing {filename} to radio...")

        wf = wave.open(filename, 'rb')
        stream = self.p.open(
            format=self.p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
            output_device_index=self.output_device
        )

        data = wf.readframes(CHUNK)
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)

        stream.stop_stream()
        stream.close()
        wf.close()
        print("Playback complete")

    def get_audio_level(self, duration=0.5):
        """Sample audio level to detect if someone is transmitting"""
        stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.input_device,
            frames_per_buffer=CHUNK
        )

        frames = []
        for _ in range(int(SAMPLE_RATE / CHUNK * duration)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(np.frombuffer(data, dtype=np.int16))

        stream.stop_stream()
        stream.close()

        audio = np.concatenate(frames)
        level = np.abs(audio).mean()
        return level

    def close(self):
        self.p.terminate()


# Test it
if __name__ == '__main__':
    audio = AudioHandler()

    # Test recording
    print("Testing audio level from radio...")
    for i in range(5):
        level = audio.get_audio_level()
        print(f"Audio level: {level:.1f}")
        time.sleep(1)

    # Record 5 seconds
    audio.record(5, 'test_rx.wav')
    print("Done - check test_rx.wav was created")

    audio.close()