import requests
import numpy as np
import scipy.io.wavfile as wavfile
import io

# Create a valid 16kHz float32 WAV file in memory
sr = 16000
audio = np.random.uniform(-1, 1, sr * 2).astype(np.float32)
buffer = io.BytesIO()
wavfile.write(buffer, sr, audio)
buffer.seek(0)
wav_bytes = buffer.read()

try:
    print("Sending POST request to enroll...")
    res = requests.post(
        'http://127.0.0.1:5001/api/enroll',
        data={'name': 'test'},
        files={'audio': ('test.wav', wav_bytes, 'audio/wav')}
    )
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Request failed:", type(e).__name__, e)
