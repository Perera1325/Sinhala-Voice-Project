# Technical References, Code Stack & Architecture Details

This document outlines the exact technical specifications, libraries, machine learning models, and architecture workflows used in the Kasundi Voice Assistant project. You can attach this as an Appendix or use it to populate the References and Implementation chapters of your thesis.

---

## 1. Core Tech Stack & Python Versions
The system is built primarily on Python, utilizing specialized libraries for audio processing, machine learning, and IoT communication.

*   **Python Version**: Python 3.9 (Recommended for maximum compatibility with TensorFlow and Librosa).
*   **Operating System**: Tested on Windows (Development) and Raspberry Pi OS (Deployment).

### Core Codebases Developed:
1.  **Machine Learning Training Stack**: `train_model.py`, `train_lid_model.py`, `dataset_augmentation.py`
2.  **Core Inference Stack**: `main_production.py`, `wakeword_engine.py`, `speaker_biometrics.py`, `nlp_classifier.py`
3.  **Web API & IoT Stack**: `app.py`, `flask_api.py`, `database.py`

---

## 2. GitHub Libraries & Their Uses

Here are the primary open-source libraries (with their GitHub repository origins) used in the project and their exact purpose:

### Machine Learning & Audio Processing
*   **TensorFlow & Keras** ([github.com/tensorflow/tensorflow](https://github.com/tensorflow/tensorflow))
    *   **Use**: Building, training, and running the Convolutional Neural Networks (CNN) for Wake Word and Primary Owner identification. Also used for converting models to `.tflite` for edge deployment.
*   **Librosa** ([github.com/librosa/librosa](https://github.com/librosa/librosa))
    *   **Use**: The core audio processing library used to load `.wav` files and extract Mel-Frequency Cepstral Coefficients (MFCCs). This is the mathematical backbone of both the machine learning models and the zero-shot speaker biometrics.
*   **SoundDevice** ([github.com/spatialaudio/python-sounddevice](https://github.com/spatialaudio/python-sounddevice))
    *   **Use**: Captures the raw audio stream from the microphone array directly into NumPy arrays for real-time processing in `main_production.py`.
*   **SciPy** ([github.com/scipy/scipy](https://github.com/scipy/scipy))
    *   **Use**: Specifically the `scipy.spatial.distance.cosine` function is used in `speaker_biometrics.py` to calculate the mathematical similarity between the live voice and the registered voice.

### Speech-to-Text & NLP
*   **SpeechRecognition** ([github.com/Uberi/speech_recognition](https://github.com/Uberi/speech_recognition))
    *   **Use**: Acts as a wrapper to interact with the Google Web Speech API. Configured to recognize Sinhala natively using the `language="si-LK"` parameter.
*   **Deep Translator** ([github.com/nidhaloff/deep-translator](https://github.com/nidhaloff/deep-translator))
    *   **Use**: Used in `nlp_classifier.py` as a fallback mechanism to translate Sinhala text to English, ensuring the NLP can robustly match intents even if the Sinhala keywords miss.

### Web Server & IoT
*   **Flask** ([github.com/pallets/flask](https://github.com/pallets/flask))
    *   **Use**: The micro web framework used in `app.py` to host the REST API endpoints. This is what allows the "Companion App" or web dashboard to register new users.
*   **Paho-MQTT** ([github.com/eclipse/paho.mqtt.python](https://github.com/eclipse/paho.mqtt.python))
    *   **Use**: The lightweight messaging protocol used to send instantaneous ON/OFF commands from the Raspberry Pi to the actual hardware relays over the local Wi-Fi network.

*(Note: While some advanced voice AI systems use frameworks like **SpeechBrain** for embedding extraction (ECAPA-TDNN), this project achieved high accuracy using a highly optimized, lightweight custom CNN and Librosa MFCC extraction, which is much better suited for low-power edge devices like the Raspberry Pi).*

---

## 3. Models Used for Training

Instead of relying on massive pre-trained models that require heavy cloud computing, this project utilizes **Custom Convolutional Neural Networks (CNNs)** built from scratch via Keras. 

### Model Architecture (`train_model.py` / `train_lid_model.py`):
1.  **Input Layer**: Accepts a 2D array of MFCC features (shape: 40 coefficients x 44-94 frames).
2.  **Batch Normalization**: Critically used as the first layer. This normalizes the audio scaling natively during training, so external scalers aren't needed during live deployment.
3.  **Convolutional Layers (Conv2D)**: Three layers (32, 64, and 128 filters) with `relu` activation and `(3,3)` kernels to detect patterns in the audio spectrum (like phonetic edges and vocal tract resonances).
4.  **Pooling (MaxPooling2D) & Dropout**: Used to downsample the data and prevent the model from overfitting (memorizing) the training data.
5.  **Dense Output**: A fully connected layer ending in a `softmax` activation to output probabilities for the specific classes (e.g., Owner vs. Unknown, or Sinhala vs. English).

---

## 4. How Accuracy Was Calculated

Accuracy in this project was derived rigorously using standard Machine Learning evaluation metrics during training:

1.  **Train/Test Split**: In `train_model.py`, the dataset is split using `sklearn` into 80% training data and 20% unseen testing data. The model is **never** trained on the test data.
2.  **Loss Function**: The model utilizes `sparse_categorical_crossentropy` to calculate the error between its prediction and the actual truth. The Adam optimizer minimizes this loss over 30-50 epochs.
3.  **Evaluation Phase**: After training, the model runs `model.evaluate(X_test, y_test)`. It attempts to classify the 20% unseen audio files. The percentage of correct guesses forms the final **Validation Accuracy** (which exceeded 95% in testing).
4.  **Biometric Accuracy (Zero-Shot)**: For the Cosine Similarity approach, accuracy was determined empirically by testing unauthorized voices. The threshold was manually tuned to **0.80 (80%)**, meaning a voice vector must be 80% mathematically similar to the enrolled vector to pass, ensuring a 0% False Acceptance Rate for intruders.

---

## 5. App Registration & IoT Architecture (What We Did)

### The "App Registration" Flow
To dynamically add secondary users without retraining the Machine Learning model:
1.  **API Endpoint**: We created the `/api/users/enroll` POST endpoint in `app.py`.
2.  **Data Ingestion**: The companion app sends the user's Name and a short `.wav` audio recording of their voice.
3.  **Feature Extraction**: The server temporarily saves the audio, strips out silence (`librosa.effects.trim`), and extracts the MFCC fingerprint, dropping the 0th coefficient to ignore volume differences.
4.  **Database Storage**: The resulting mathematical vector is converted to JSON and stored permanently in `voice_users.db` via SQLite3.

### The MQTT & Control Flow
When a verified voice issues a command:
1.  **NLP Resolution**: `nlp_classifier.py` determines the target (e.g., `device_id="light_1"`) and action (`action="ON"`).
2.  **REST API Trigger**: The main loop sends this JSON payload to `/api/devices/control`.
3.  **MQTT Publish**: The Flask server takes the payload and publishes the string "ON" to the specific MQTT topic: `home/devices/light_1/ch1/set`.
4.  **Hardware Actuation**: An ESP8266 or similar microcontroller subscribed to that topic instantly triggers the relay, turning on the physical light.
