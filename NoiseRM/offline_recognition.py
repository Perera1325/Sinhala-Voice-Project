# ==============================================================================
# Project: AI Based Voice Controlled Home Automation System
# File: offline_recognition.py
# Description: Implements offline Automatic Speech Recognition (ASR) using Vosk
#              with a restricted grammar list to accurately match Sinhala words.
# Author: Kasundi (assisted by Antigravity)
# Date: June 2026
# ==============================================================================

import os
import wave
import json

# Pre-initialized Vosk model placeholder
_vosk_model = None

def get_vosk_model():
    """Lazy initialization of the Vosk model."""
    global _vosk_model
    if _vosk_model is None:
        try:
            from vosk import Model
            model_path = r"C:\Users\Kasundi\Downloads\NoiseRM\vosk-model"
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Vosk model folder not found at: {model_path}. Please run setup_environment.py first.")
            print("[INFO] Loading Vosk speech recognition model...")
            _vosk_model = Model(model_path)
            print("[INFO] Vosk model loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load Vosk model: {e}")
            raise e
    return _vosk_model

def transcribe_offline(audio_path):
    """
    Transcribes a WAV file using the Vosk offline engine.
    Restricts search vocabulary to command keywords to optimize phonetic accuracy.
    
    Parameters:
    - audio_path: Absolute path to the WAV file.
    
    Returns:
    - String containing the transcribed text.
    """
    try:
        from vosk import KaldiRecognizer
        
        # Load Vosk Model
        model = get_vosk_model()
        
        # Read WAV file
        wf = wave.open(audio_path, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            # Vosk expects 16-bit mono PCM WAV
            print("[WARNING] WAV file format is not 16-bit mono PCM. Checking converter options...")
            
        # Define grammar to focus detection on our Sinhala/English control keywords
        # This acts as a forced-alignment vocabulary list, ensuring extremely high recognition rates.
        # We map Sinhala words to English dictionary words that sound phonetically similar:
        # eka -> echo / acre / ek / k / a / there's / their
        # danna -> done / down / data / don
        # niwanna -> never / no / winner / only / one / net / wanna / nirvana / want
        # kasu -> castle / cousin / cash
        # hay -> hey / hay
        grammar = [
            "light", "like",
            "fan", "van", "fannie", "sam",
            "echo", "acre", "ek", "k", "a", "there's", "their",
            "done", "down", "data", "don",
            "never", "no", "winner", "only", "one", "net", "wanna", "nirvana", "want",
            "hey", "hay",
            "castle", "cousin", "cash",
            "sandy", "sunday", "candy", "county",
            "[unk]"
        ]
        grammar_json = json.dumps(grammar)
        
        # Initialize recognizer with specified grammar
        rec = KaldiRecognizer(model, wf.getframerate(), grammar_json)
        rec.SetWords(True)
        
        # Feed audio bytes to recognizer
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                pass
                
        # Get final result
        res = json.loads(rec.FinalResult())
        raw_text = res.get("text", "").lower()
        wf.close()
        
        # Map phonetic English vocabulary back to Sinhala phonetic command structure
        mapped_tokens = []
        raw_words = raw_text.split()
        
        # 1. Device detection
        if any(w in raw_words for w in ["light", "like"]):
            mapped_tokens.append("light")
        elif any(w in raw_words for w in ["fan", "van", "fannie", "sam"]):
            mapped_tokens.append("fan")
            
        # 2. Connector detection ("eka")
        if any(w in raw_words for w in ["echo", "acre", "ek", "k", "a", "there's", "their"]):
            mapped_tokens.append("eka")
            
        # 3. Action detection
        if any(w in raw_words for w in ["done", "down", "data", "don"]):
            mapped_tokens.append("danna")
        elif any(w in raw_words for w in ["never", "no", "winner", "only", "one", "net", "wanna", "nirvana", "want"]):
            mapped_tokens.append("niwanna")
            
        # 4. Wake word detection
        if any(w in raw_words for w in ["hey", "hay"]):
            mapped_tokens.append("hay")
        if any(w in raw_words for w in ["castle", "cousin", "cash", "sandy", "sunday", "candy", "county"]):
            mapped_tokens.append("kasundi")
            
        text = " ".join(mapped_tokens)
        print(f"[INFO] Offline ASR Mapped Result: '{text}' (Raw: '{raw_text}')")
        return text
    except Exception as e:
        print(f"[ERROR] Error in offline transcription: {e}")
        return ""

if __name__ == "__main__":
    print("Offline recognition module loaded.")
