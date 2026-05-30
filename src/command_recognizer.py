import numpy as np
import tensorflow as tf
import librosa

# Configuration
SAMPLE_RATE = 16000
CONFIDENCE_THRESHOLD = 40.0

# Load Model
# Currently loads the model trained for "Light eka danna".
# To support all 6 commands natively, this model should be retrained on 
# a 7-class dataset (Light On, Light Off, Fan On, Fan Off, Curtain Open, Curtain Close, Unknown)
interpreter = tf.lite.Interpreter(model_path="light_model.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

COMMANDS = {
    0: "LIGHT_ON",
    1: "UNKNOWN",
    # Future classes:
    # 2: "LIGHT_OFF",
    # 3: "FAN_ON",
    # 4: "FAN_OFF",
    # 5: "CURTAIN_OPEN",
    # 6: "CURTAIN_CLOSE"
}

def extract_mfcc(audio_data, n_mfcc=40, n_frames=44):
    audio_data = np.asarray(audio_data, dtype=np.float32).flatten()
    mfcc = librosa.feature.mfcc(y=audio_data, sr=SAMPLE_RATE, n_mfcc=n_mfcc)
    mfcc = mfcc[:, :n_frames]
    
    if mfcc.shape[1] < n_frames:
        pad_width = n_frames - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    return mfcc

def recognize_command(audio_data):
    """
    Analyzes the audio and returns the detected Sinhala command and confidence.
    """
    mfcc = extract_mfcc(audio_data)
    input_data = mfcc.reshape(1, 40, 44, 1).astype(np.float32)

    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    prediction = interpreter.get_tensor(output_details[0]['index'])
    
    confidence = float(np.max(prediction)) * 100
    predicted_index = np.argmax(prediction)
    
    if confidence >= CONFIDENCE_THRESHOLD:
        return COMMANDS.get(predicted_index, "UNKNOWN"), confidence
    else:
        return "UNKNOWN", confidence
