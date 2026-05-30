import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_SET_DIR = os.path.join(BASE_DIR, "Data_Set")
AUGMENTED_DIR = os.path.join(BASE_DIR, "Augmented_Data")
MODELS_DIR = BASE_DIR

# Audio Processing Parameters
SAMPLE_RATE = 16000     # Required: 16kHz
DURATION = 1.0          # 1 second of audio per frame/command
N_MFCC = 40             # Number of MFCC features
N_FFT = 2048            # FFT window size
HOP_LENGTH = 512        # Hop length for STFT
MAX_PAD_LEN = int((SAMPLE_RATE * DURATION) / HOP_LENGTH) + 1  # Expected number of MFCC frames: ~32 for 1 sec

# Machine Learning Parameters
CLASSES = {0: "LIGHT_ON", 1: "UNKNOWN"}
NUM_CLASSES = len(CLASSES)
EPOCHS = 50
BATCH_SIZE = 32

# Thresholds
CONFIDENCE_THRESHOLD = 0.85
RMS_ENERGY_THRESHOLD = 0.015  # Minimum volume level to be considered "speech" and not silence

# Flask / MQTT settings (Placeholders for integration)
FLASK_API_URL = "http://127.0.0.1:5000/command"
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_TOPIC = "home/livingroom/light"
