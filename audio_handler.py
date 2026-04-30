import pyaudio
import sounddevice as sd
import scipy.io.wavfile as wavfile
import wave
import numpy as np
import time

SAMPLE_RATE = 8000
CHUNK       = 1024
FORMAT      = pyaudio.paInt16
CHANNELS    = 1


def pyaudio_to_sounddevice_index(pyaudio_index):
    """
    Map a PyAudio device index to a sounddevice index by matching device name.
    They enumerate differently on Windows so we match by name.
    """
    p    = pyaudio.PyAudio()
    info = p.get_device_info_by_index(pyaudio_index)
    pa_name = info['name']
    p.terminate()

    # Find matching sounddevice device by name fragment
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if (pa_name[:20] in dev['name'] or dev['name'][:20] in pa_name):
            if dev['max_output_channels'] > 0:
                print(f"Mapped PyAudio {pyaudio_index} -> sounddevice {i} ({dev['name']})")
                return i

    # Try looser match
    for i, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            # Match first significant words
            pa_words  = set(pa_name.lower().split()[:3])
            sd_words  = set(dev['name'].lower().split()[:3])
            if pa_words & sd_words:
                print(f"Loose mapped PyAudio {pyaudio_index} -> sounddevice {i} ({dev['name']})")
                return i

    print(f"Could not map PyAudio {pyaudio_index} to sounddevice - using default")
    return None


def find_working_output(pyaudio_index):
    """
    Given a PyAudio output device index, find a working one.
    Tests at the WAV sample rate to avoid -9999 errors.
    Falls back to auto-detect if supplied index fails.
    """
    p = pyaudio.PyAudio()

    # Test supplied device
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            output=True,
            output_device_index=pyaudio_index,
            frames_per_buffer=CHUNK
        )
        stream.close()
        p.terminate()
        return pyaudio_index
    except Exception:
        print(f"Output device {pyaudio_index} failed at {SAMPLE_RATE}Hz - searching...")

    # Search for first working USB audio output
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxOutputChannels'] == 0:
            continue
        try:
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                output_device_index=i,
                frames_per_buffer=CHUNK
            )
            stream.close()
            print(f"Found working output device: {i} - {info['name']}")
            p.terminate()
            return i
        except Exception:
            continue

    p.terminate()
    return None


def find_working_input(pyaudio_index):
    """
    Given a PyAudio input device index, find a working one.
    """
    p = pyaudio.PyAudio()

    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=pyaudio_index,
            frames_per_buffer=CHUNK
        )
        stream.close()
        p.terminate()
        return pyaudio_index
    except Exception:
        print(f"Input device {pyaudio_index} failed - searching...")

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] == 0:
            continue
        try:
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=i,
                frames_per_buffer=CHUNK
            )
            stream.close()
            print(f"Found working input device: {i} - {info['name']}")
            p.terminate()
            return i
        except Exception:
            continue

    p.terminate()
    return None


class AudioHandler:
    def __init__(self, input_device=None, output_device=None):
        # Verify or find working PyAudio devices
        self.input_device  = find_working_input(input_device) \
            if input_device  is not None else find_working_input(0)
        self.output_device = find_working_output(output_device) \
            if output_device is not None else find_working_output(0)

        # Map output to sounddevice index for thread-safe playback
        if self.output_device is not None:
            self.sd_output = pyaudio_to_sounddevice_index(self.output_device)
        else:
            self.sd_output = None

        print(f"Audio ready - input={self.input_device} "
              f"output={self.output_device} "
              f"sd_output={self.sd_output}")

    def play(self, filename):
        """
        Play WAV file to radio TX output.
        Uses sounddevice for thread-safe playback on Windows.
        Falls back to PyAudio if sounddevice fails.
        """
        print(f"Playing {filename}...")

        if self.sd_output is not None:
            try:
                sample_rate, data = wavfile.read(filename)

                # Convert to float32
                if data.dtype == np.int16:
                    audio = data.astype(np.float32) / 32768.0
                elif data.dtype == np.int32:
                    audio = data.astype(np.float32) / 2147483648.0
                else:
                    audio = data.astype(np.float32)

                # Ensure mono
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)

                sd.play(
                    audio,
                    samplerate=sample_rate,
                    device=self.sd_output,
                    blocking=True
                )
                sd.wait()
                print("Playback complete")
                return

            except Exception as e:
                print(f"sounddevice failed: {e} - trying PyAudio...")

        # PyAudio fallback
        self._play_pyaudio(filename)

    def _play_pyaudio(self, filename):
        """PyAudio playback fallback"""
        p  = pyaudio.PyAudio()
        wf = wave.open(filename, 'rb')

        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
            output_device_index=self.output_device,
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
        print("PyAudio playback complete")

    def get_audio_level(self, duration=0.5):
        """Sample audio level to detect incoming signal"""
        try:
            p      = pyaudio.PyAudio()
            stream = p.open(
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
            p.terminate()

            return float(np.abs(np.concatenate(frames)).mean())

        except Exception as e:
            print(f"Audio level error: {e}")
            return 0.0

    def record(self, duration, filename='rx_audio.wav'):
        """Record audio from radio RX input"""
        p      = pyaudio.PyAudio()
        stream = p.open(
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
        p.terminate()

        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        return filename

    def close(self):
        sd.stop()

    @staticmethod
    def list_devices():
        """List all available audio devices from both PyAudio and sounddevice"""
        print("\n--- PyAudio devices ---")
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            ins  = info['maxInputChannels']
            outs = info['maxOutputChannels']
            if ins > 0 or outs > 0:
                direction = []
                if ins  > 0: direction.append('IN')
                if outs > 0: direction.append('OUT')
                print(
                    f"  {i:2d}: [{'/'.join(direction):6s}] "
                    f"{info['name']}"
                )
        p.terminate()

        print("\n--- sounddevice devices ---")
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            ins  = dev['max_input_channels']
            outs = dev['max_output_channels']
            if ins > 0 or outs > 0:
                direction = []
                if ins  > 0: direction.append('IN')
                if outs > 0: direction.append('OUT')
                print(
                    f"  {i:2d}: [{'/'.join(direction):6s}] "
                    f"{dev['name']}"
                )


if __name__ == '__main__':
    AudioHandler.list_devices()
    print()
    audio = AudioHandler()
    print(f"\nInput  device (PyAudio):    {audio.input_device}")
    print(f"Output device (PyAudio):    {audio.output_device}")
    print(f"Output device (sounddevice):{audio.sd_output}")
    print("\nMonitoring audio levels for 10 seconds...")
    for i in range(20):
        level = audio.get_audio_level()
        bars  = int(level / 30) * '█'
        print(f"Level: {level:6.0f}  {bars}")
        time.sleep(0.5)