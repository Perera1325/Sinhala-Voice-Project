# ==============================================================================
# Project: AI Based Voice Controlled Home Automation System
# File: mqtt_client.py
# Description: Implements the MQTT publisher client to send control commands
#              ("ON" or "OFF") to the ESP32 micro-controller.
# Author: Kasundi (assisted by Antigravity)
# Date: June 2026
# ==============================================================================

import paho.mqtt.client as mqtt
import time

# MQTT Broker parameters (using a public sandbox broker)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_PREFIX = "home/livingroom/"
TOPIC_LIGHT = TOPIC_PREFIX + "light"
TOPIC_FAN = TOPIC_PREFIX + "fan"

# Global client instance to keep a persistent connection
_client = None

def get_mqtt_client():
    """Returns a connected, running MQTT client instance (cached)."""
    global _client
    if _client is not None:
        return _client
        
    print(f"[MQTT] Initializing persistent connection to broker: {MQTT_BROKER}:{MQTT_PORT}")
    try:
        try:
            client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            # Fallback for older paho-mqtt versions
            client = mqtt.Client()
            
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        _client = client
        return _client
    except Exception as e:
        print(f"[ERROR] MQTT connection failed: {e}")
        return None

def publish_command(device, action):
    """
    Publishes an ON or OFF command to the appropriate MQTT topic.
    Uses a persistent background client connection to ensure sub-second response times.
    """
    device_lower = device.lower()
    action_upper = action.upper()
    
    # Map device names to topics
    if "light" in device_lower:
        topic = TOPIC_LIGHT
    elif "fan" in device_lower:
        topic = TOPIC_FAN
    else:
        print(f"[ERROR] Unknown device: '{device}'")
        return False
        
    if action_upper not in ["ON", "OFF"]:
        print(f"[ERROR] Invalid action: '{action}'")
        return False

    client = get_mqtt_client()
    if client is None:
        print("[ERROR] Cannot publish: MQTT client is not connected.")
        return False
        
    try:
        # Publish payload
        print(f"[MQTT] Publishing to '{topic}': {action_upper}")
        info = client.publish(topic, action_upper, qos=1)
        
        # Wait up to 1.0 second for delivery confirmation (avoid blocking the HTTP thread indefinitely)
        try:
            info.wait_for_publish(timeout=1.0)
            print("[OK] MQTT command published and acknowledged.")
        except RuntimeError:
            print("[WARNING] MQTT publish call did not receive ACK within 1s (sent in background).")
            
        return True
    except Exception as e:
        print(f"[ERROR] MQTT publication failed: {e}")
        # Reset the client so it reconnects on the next call
        global _client
        if _client is not None:
            try:
                _client.loop_stop()
                _client.disconnect()
            except Exception:
                pass
            _client = None
        return False

if __name__ == "__main__":
    # Self-test block: Publish ON command to light
    print("Running MQTT client test...")
    publish_command("light", "ON")
    time.sleep(2)  # Give loop time to complete

