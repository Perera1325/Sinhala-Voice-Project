#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// --- Configuration ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

const int RELAY_PIN = 26; // Change to the GPIO pin connected to your relay

WebServer server(5000); // Running on port 5000 to match RPi python script

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Assume LOW means relay is off

  // Connect to Wi-Fi
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected.");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());

  // Define HTTP Endpoint matching the Raspberry Pi POST request
  server.on("/channels/b21642ae-34f1-485c-b459-351bafcdf920/control", HTTP_POST, handleControlRequest);

  server.begin();
  Serial.println("HTTP server started.");
}

void loop() {
  server.handleClient();
}

void handleControlRequest() {
  if (server.hasArg("plain") == false) {
    server.send(400, "application/json", "{\"status\":\"error\", \"message\":\"Body not received\"}");
    return;
  }

  String body = server.arg("plain");
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    server.send(400, "application/json", "{\"status\":\"error\", \"message\":\"Invalid JSON\"}");
    return;
  }

  String value = doc["value"];
  
  if (value == "ON") {
    Serial.println("Received command: LIGHT ON");
    digitalWrite(RELAY_PIN, HIGH); // Turn relay ON
    server.send(200, "application/json", "{\"status\":\"success\", \"message\":\"Relay turned ON\"}");
  } 
  else if (value == "OFF") {
    Serial.println("Received command: LIGHT OFF");
    digitalWrite(RELAY_PIN, LOW); // Turn relay OFF
    server.send(200, "application/json", "{\"status\":\"success\", \"message\":\"Relay turned OFF\"}");
  } 
  else {
    server.send(400, "application/json", "{\"status\":\"error\", \"message\":\"Invalid command value\"}");
  }
}
