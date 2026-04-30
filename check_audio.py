import pyaudio

p = pyaudio.PyAudio()
print("All output-capable devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxOutputChannels'] > 0:
        print(f"  {i:2d}: {info['name']} - SR:{int(info['defaultSampleRate'])}Hz")
p.terminate()

# Now test opening the USB Audio device specifically
print("\nTesting USB Audio CODEC output...")
p2 = pyaudio.PyAudio()
for i in range(p2.get_device_count()):
    info = p2.get_device_info_by_index(i)
    if 'USB Audio CODEC' in info['name'] and info['maxOutputChannels'] > 0:
        print(f"Found at index {i}: {info['name']}")
        try:
            stream = p2.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=8000,
                output=True,
                output_device_index=i,
                frames_per_buffer=1024
            )
            stream.close()
            print(f"  ✅ Device {i} opened successfully at 8000Hz")
        except Exception as e:
            print(f"  ❌ Device {i} failed at 8000Hz: {e}")
            # Try with device's native sample rate
            native_rate = int(info['defaultSampleRate'])
            try:
                stream = p2.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=native_rate,
                    output=True,
                    output_device_index=i,
                    frames_per_buffer=1024
                )
                stream.close()
                print(f"  ✅ Device {i} works at native rate {native_rate}Hz")
            except Exception as e2:
                print(f"  ❌ Device {i} also failed at {native_rate}Hz: {e2}")
p2.terminate()