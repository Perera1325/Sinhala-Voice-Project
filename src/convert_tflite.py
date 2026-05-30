import os
import tensorflow as tf
from config import MODELS_DIR

def main():
    h5_model_path = os.path.join(MODELS_DIR, "light_model.h5")
    tflite_model_path = os.path.join(MODELS_DIR, "light_model.tflite")
    
    if not os.path.exists(h5_model_path):
        print(f"Error: Could not find model at {h5_model_path}. Please run train_model.py first.")
        return
        
    print(f"Loading Keras model from {h5_model_path}...")
    model = tf.keras.models.load_model(h5_model_path)
    
    print("Converting to TensorFlow Lite format...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # Optimization for edge devices (Raspberry Pi 4)
    # This applies dynamic range quantization, reducing model size by 4x
    # and improving CPU execution speed, with negligible accuracy loss.
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    
    tflite_model = converter.convert()
    
    with open(tflite_model_path, "wb") as f:
        f.write(tflite_model)
        
    print(f"Success! Saved TFLite model to {tflite_model_path}")
    
    # Test loading the TFLite model to ensure it works
    try:
        interpreter = tf.lite.Interpreter(model_content=tflite_model)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        print("\nTFLite Model Details:")
        print(f"Input shape: {input_details[0]['shape']}")
        print(f"Input type: {input_details[0]['dtype']}")
        print(f"Output shape: {output_details[0]['shape']}")
        print(f"Output type: {output_details[0]['dtype']}")
        print("\nReady for deployment on Raspberry Pi!")
        
    except Exception as e:
        print(f"Error verifying TFLite model: {e}")

if __name__ == "__main__":
    main()
