# ==============================================================================
# Project: AI Based Voice Controlled Home Automation System
# File: flask_server.py
# Description: Implements a Flask web server on the Raspberry Pi 4 that exposes 
#              a command endpoint to receive HTTP requests and route them via MQTT.
# Author: Kasundi (assisted by Antigravity)
# Date: June 2026
# ==============================================================================

from flask import Flask, request, jsonify
import os
import sys

# Add target directory to Python path if necessary to find local modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import mqtt_client

app = Flask(__name__)

# Device Channel ID Mapping Configuration
CHANNEL_TO_DEVICE = {
    "5508f5fc-3641-44cd-9cc5-87e5fc677483": "light",
    "74136aa1-471d-485d-ac02-9c0bb408d9d3": "fan"
}

@app.route('/channels/<channel_id>/control', methods=['POST'])
def handle_channel_control(channel_id):
    """
    Handles control requests via channel UUID route parameter.
    Expects URL: /channels/<channel_id>/control
    Expects JSON payload: {"action": "ON"|"OFF"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload provided."}), 400
            
        action = data.get("action")
        if not action:
            action = data.get("command")
        if not action:
            # Fallback if state is passed
            action = data.get("state")
            
        if not action:
            return jsonify({"status": "error", "message": "Missing required field 'action'."}), 400
            
        action = action.upper()
        
        # Look up device name by channel ID
        device = CHANNEL_TO_DEVICE.get(channel_id)
        if not device:
            # Fallback check inside payload
            device = data.get("device", "light").lower()
            print(f"[Flask Server WARNING] Unknown channel ID '{channel_id}'. Mapping fallback to device '{device}'")
            
        print(f"[Flask Server] Received channel control: Channel = '{channel_id}' ({device.upper()}), Action = '{action}'")
        
        import threading
        # Run MQTT publish in a daemonized background thread
        threading.Thread(
            target=mqtt_client.publish_command, 
            args=(device, action), 
            daemon=True
        ).start()
        
        return jsonify({
            "status": "success", 
            "message": f"Command queued successfully for {device.upper()} = {action}"
        }), 200
        
    except Exception as e:
        print(f"[Flask Server ERROR] Exception in channel control handler: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/command', methods=['POST'])
def handle_command():
    """
    Handles command execution requests.
    Expects JSON payload: {"device": "light"|"fan", "action": "ON"|"OFF"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload provided."}), 400
            
        device = data.get("device")
        action = data.get("action")
        
        if not device or not action:
            return jsonify({"status": "error", "message": "Missing required fields 'device' or 'action'."}), 400
            
        print(f"[Flask Server] Received command request: Device = '{device}', Action = '{action}'")
        
        import threading
        # Run the MQTT publish in a daemonized background thread to prevent blocking the HTTP response
        threading.Thread(
            target=mqtt_client.publish_command, 
            args=(device, action), 
            daemon=True
        ).start()
        
        return jsonify({
            "status": "success", 
            "message": f"Command queued successfully for background publish to {device.upper()} = {action.upper()}"
        }), 200
            
    except Exception as e:
        print(f"[Flask Server ERROR] Exception in command handler: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Simple health check endpoint."""
    return jsonify({"status": "online", "message": "Home Automation API Server is running."}), 200

if __name__ == '__main__':
    print("Starting Flask Command Routing Server...")
    print("Listening on http://0.0.0.0:5000/ (port 5000)")
    # Listen on all network adapters so other devices in the home LAN can send control payloads
    app.run(host='0.0.0.0', port=5000, debug=False)
