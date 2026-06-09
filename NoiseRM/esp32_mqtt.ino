/*
==============================================================================
Project: AI Based Voice Controlled Home Automation System
File: esp32_mqtt.ino
Description: Arduino sketch for the ESP32 microcontroller to connect to Wi-Fi,
             subscribe to MQTT topics, and switch relays for Light and Fan.
Author: Kasundi (assisted by Antigravity)
Date: June 2026
==============================================================================
Required Libraries:
- PubSubClient by Nick O'Leary (Install via Arduino Library Manager)
- WiFi (Built-in ESP32 WiFi library)
==============================================================================
*/

#include <WiFi.h>
#include <PubSubClient.h>

// Wi-Fi Connection Details (Change to your local credentials)
const char* ssid = "HayKasu";
const char* password = "1234567890@";

// MQTT Broker Details (using the HiveMQ public broker)
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;

// MQTT Topic Definitions
const char* topic_light = "home/livingroom/light";
const char* topic_fan   = "home/livingroom/fan";

// Pin Configuration for Relays
const int RELAY_LIGHT_PIN = 18;  // GPIO 18 connected to Light Relay
const int RELAY_FAN_PIN   = 19;  // GPIO 19 connected to Fan Relay

// Initialize WiFi and MQTT clients
WiFiClient espClient;
PubSubClient client(espClient);

// ==============================================================================
// WIFI SETUP FUNCTION
// ==============================================================================
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to Wi-Fi Network: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("[Wi-Fi] Connected successfully!");
  Serial.print("[Wi-Fi] IP Address: ");
  Serial.println(WiFi.localIP());
}

// ==============================================================================
// MQTT CALLBACK FUNCTION (HANDLE RECEIVED MESSAGES)
// ==============================================================================
void callback(char* topic, byte* payload, unsigned int length) {
  // Convert payload bytes to a string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("[MQTT] Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  Serial.println(message);

  // ----------------------------------------------------
  // LIGHT RELAY CONTROL logic
  // ----------------------------------------------------
  if (strcmp(topic, topic_light) == 0) {
    if (message == "ON") {
      Serial.println("[RELAY] Turning LIGHT ON...");
      digitalWrite(RELAY_LIGHT_PIN, HIGH);  // Active-High Relay (use LOW for Active-Low)
    } else if (message == "OFF") {
      Serial.println("[RELAY] Turning LIGHT OFF...");
      digitalWrite(RELAY_LIGHT_PIN, LOW);
    }
  }
  
  // ----------------------------------------------------
  // FAN RELAY CONTROL logic
  // ----------------------------------------------------
  else if (strcmp(topic, topic_fan) == 0) {
    if (message == "ON") {
      Serial.println("[RELAY] Turning FAN ON...");
      digitalWrite(RELAY_FAN_PIN, HIGH);
    } else if (message == "OFF") {
      Serial.println("[RELAY] Turning FAN OFF...");
      digitalWrite(RELAY_FAN_PIN, LOW);
    }
  }
}

// ==============================================================================
// MQTT RECONNECT FUNCTION
// ==============================================================================
void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("[MQTT] Attempting connection to broker...");
    // Create a unique client ID based on MAC address
    String clientId = "ESP32Client-HomeAutomation-";
    clientId += String(random(0xffff), HEX);
    
    // Connect to broker
    if (client.connect(clientId.c_str())) {
      Serial.println("CONNECTED!");
      
      // Subscribe to device control topics
      client.subscribe(topic_light);
      client.subscribe(topic_fan);
      Serial.println("[MQTT] Subscribed to topic_light and topic_fan.");
    } else {
      Serial.print("[MQTT] connection failed, rc=");
      Serial.print(client.state());
      Serial.println(". Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

// ==============================================================================
// INITIAL SETUP
// ==============================================================================
void setup() {
  // Initialize Serial port for debugging
  Serial.begin(115200);
  
  // Set relay pins as output and set default states (OFF)
  pinMode(RELAY_LIGHT_PIN, OUTPUT);
  pinMode(RELAY_FAN_PIN, OUTPUT);
  digitalWrite(RELAY_LIGHT_PIN, LOW);
  digitalWrite(RELAY_FAN_PIN, LOW);
  
  // Connect to WiFi
  setup_wifi();
  
  // Setup MQTT server and callback handler
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

// ==============================================================================
// MAIN EXECUTION LOOP
// ==============================================================================
void loop() {
  // Ensure MQTT client stays connected
  if (!client.connected()) {
    reconnect();
  }
  
  // Maintain client connections and check for incoming messages
  client.loop();
}
