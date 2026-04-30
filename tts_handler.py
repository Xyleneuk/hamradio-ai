import pyttsx3
import wave
import os

class TTSHandler:
    def __init__(self, output_device_index=7):
        self.engine = pyttsx3.init()
        self.output_device = output_device_index
        
        # Set voice properties for radio-friendly speech
        self.engine.setProperty('rate', 150)     # Words per minute - slightly slow for clarity
        self.engine.setProperty('volume', 1.0)   # Full volume
        
        # Try to find a good English voice
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                print(f"Using voice: {voice.name}")
                break

    def speak(self, text):
        """Speak text through default audio output"""
        print(f"Speaking: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def speak_to_file(self, text, filename='tx_audio.wav'):
        """Save speech to WAV file using Windows SAPI directly"""
        import win32com.client
        import time
        
        print(f"Generating audio: {text}")
        
        sapi = win32com.client.Dispatch("SAPI.SpVoice")
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        
        # Open file for writing
        stream.Open(filename, 3, False)  # 3 = SSFMCreateForWrite
        sapi.AudioOutputStream = stream
        sapi.Rate = -2  # Slightly slower for clarity
        sapi.Speak(text)
        stream.Close()
        
        print(f"Saved to {filename}")
        return filename

    def list_voices(self):
        """List available TTS voices"""
        voices = self.engine.getProperty('voices')
        for i, voice in enumerate(voices):
            print(f"{i}: {voice.name} ({voice.id})")

    def set_voice_by_index(self, index):
        voices = self.engine.getProperty('voices')
        if index < len(voices):
            self.engine.setProperty('voice', voices[index].id)
            print(f"Voice set to: {voices[index].name}")


# Test it
if __name__ == '__main__':
    tts = TTSHandler()
    
    print("\nAvailable voices:")
    tts.list_voices()
    
    print("\nTesting speech output...")
    tts.speak("CQ CQ CQ, this is Mike X-ray Zero Mike X-ray Oscar, calling CQ and standing by")
    
    print("\nSaving to file...")
    tts.speak_to_file(
        "Golf Four Alpha Bravo Charlie, this is Mike X-ray Zero Mike X-ray Oscar, good day",
        'test_tx.wav'
    )
    print("Done - check test_tx.wav was created")