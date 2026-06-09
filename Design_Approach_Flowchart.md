# System Architecture & Design Approach Flowchart

Here is the fully accurate architectural flowchart representing your entire system. It includes the new analytical noise reduction pipeline, the hybrid biometric security, the dual online/offline routing, and the Flutter/ESP32 hardware integration.

```mermaid
graph TD
    classDef hardware fill:#2d3748,stroke:#4a5568,stroke-width:2px,color:#fff;
    classDef software fill:#2b6cb0,stroke:#2c5282,stroke-width:2px,color:#fff;
    classDef process fill:#805ad5,stroke:#553c9a,stroke-width:2px,color:#fff;
    classDef decision fill:#c53030,stroke:#9b2c2c,stroke-width:2px,color:#fff;
    classDef mobile fill:#00b5d8,stroke:#00838f,stroke-width:2px,color:#fff;
    classDef highlight fill:#d69e2e,stroke:#b7791f,stroke-width:2px,color:#fff;

    %% Input Layer
    User((User Voice Command)):::hardware -- "Sinhala / English" --> Mic[Microphone Array]:::hardware
    Flutter[Flutter Mobile App]:::mobile <-->|HTTP REST / MQTT LWT| Flask[Flask API & MQTT Broker]:::software
    
    %% Analytical Noise Reduction Pipeline
    Mic --> |Raw Audio| NoiseBlock{Analytical Noise Pipeline}:::highlight
    
    subgraph NoiseBlock [Noise Reduction & Evaluation]
        direction TB
        Input[Clean Audio + Ambient Background Noise]:::process
        Input --> Baseline[Baseline Methods: Spectral, Static Wiener]:::process
        Input --> Custom[Custom Dynamic Noise Filter]:::highlight
        Baseline --> Compare{Evaluate Audio Fidelity}:::decision
        Custom --> Compare
    end
    
    Compare -->|Select Superior Output| BestClean[Optimized Clean Voice]:::process
    
    %% Security Layer
    BestClean --> Biometrics{Speaker Verification}:::decision
    Biometrics -->|"Access Denied"| Reject[Reject Command & Sound Alert]:::hardware
    Biometrics -->|"Authenticated"| Router{Network Availability}:::decision
    
    %% ASR Layer (Dual Pipeline)
    Router -->|"Internet Available"| Online[Online Cloud Pipeline: Google STT]:::software
    Router -->|"Offline Mode"| Offline[Offline Edge Pipeline: Vosk Local Model]:::software
    
    Online --> NLP[NLP Intent Classifier]:::process
    Offline --> NLP
    
    %% Central Hub
    NLP -->|"Extract Device ID & Action"| RPI(Raspberry Pi 4 Central Hub):::hardware
    RPI --> Flask
    
    %% IoT Physical Layer
    Flask -->|"MQTT Publish Payload"| ESP32[ESP32 Microcontrollers]:::hardware
    ESP32 -->|"Actuate Relays"| Appliance((Household Appliances)):::hardware
    
    %% Status Loop
    ESP32 -->|"MQTT Status Broadcast"| Flask
```

> [!TIP]
> **How to use this in your thesis:**
> This diagram is rendered automatically. You can right-click on the flowchart above and select **"Copy image"** or take a screenshot, and place it directly into your Microsoft Word document under the *System Flow Chart* or *Design Approach* section!
