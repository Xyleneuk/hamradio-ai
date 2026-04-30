import whisper
import numpy as np

class Transcriber:
    def __init__(self, model_size='base'):
        print(f"Loading Whisper {model_size} model...")
        self.model = whisper.load_model(model_size)
        print("Whisper ready")

    def transcribe(self, audio_file):
        """Transcribe audio file to text"""
        print(f"Transcribing {audio_file}...")
        
        result = self.model.transcribe(
            audio_file,
            language='en',
            fp16=False  # Use fp32 for CPU compatibility
        )
        
        text = result['text'].strip()
        print(f"Transcribed: {text}")
        return text

    def transcribe_with_confidence(self, audio_file):
        """Transcribe and return text with confidence segments"""
        result = self.model.transcribe(
            audio_file,
            language='en',
            fp16=False,
            verbose=False
        )
        
        text = result['text'].strip()
        segments = result.get('segments', [])
        
        # Average confidence across segments
        if segments:
            avg_confidence = np.mean([s.get('avg_logprob', 0) for s in segments])
        else:
            avg_confidence = 0
            
        return {
            'text': text,
            'confidence': avg_confidence,
            'segments': segments
        }


# Test it
if __name__ == '__main__':
    transcriber = Transcriber(model_size='base')
    
    # Test with the recording we made earlier
    import os
    if os.path.exists('test_rx.wav'):
        result = transcriber.transcribe_with_confidence('test_rx.wav')
        print(f"\nText: {result['text']}")
        print(f"Confidence: {result['confidence']:.3f}")
    else:
        print("No test_rx.wav found - run audio_handler.py first")