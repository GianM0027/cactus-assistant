// Including required libraries for the project
#include <InfluxDbClient.h>
#include "Arduino.h"
#include "Audio.h"
#include "SD.h"
#include "FS.h"
#include <WiFi.h> 
#include <WebServer.h>
#include <DHT.h>
#include <DHT_U.h>

// Creating a WebServer instance on port 80
WebServer server(80);

// Definitions for the DHT11 sensor (temperature and humidity)
#define DHTPIN 2
#define DHTTYPE DHT11 

DHT dht(DHTPIN, DHTTYPE);

 
// Connections for the microSD card reader
#define SD_CS         15
#define SPI_MOSI      23 
#define SPI_MISO      18
#define SPI_SCK       19
 
// Connections for I2S (audio interface)
#define I2S_DOUT      22
#define I2S_BCLK      26
#define I2S_LRC       25

// Language for TTS (Text-to-Speech)
#define TTS_GOOGLE_LANGUAGE "it-IT" // it-IT en-GB fr-FR es-ES

// Button pin to start audio recording
#define BUTTON_PIN 4

// Wi-Fi network name and password
#define SSID_WIFI "House of Pong #Gast" //Mauro's iPhone Big Chungus Leonardo Hotel
#define PSW "pingpong020" //giggino123 123abc!@#ABC

// Name of the audio file
#define AUDIO_FILE "/Audio.wav"  
 
// Create Audio object
Audio audio;
String phrase = "Default phrase, something happened";

// Function declarations
bool I2S_Record_Init();
bool Record_Start(String filename);
bool Record_Available(String filename, float* audiolength_sec);
 
void setup() {

  // Initializing serial communication
  Serial.begin(115200);

  // Setting up the button
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // Initializing the DHT11 sensor for temperature and humidity
  dht.begin();
  Serial.println("DHT sensor started");

  // Connecting to WLAN
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID_WIFI, PSW); //WiFi.begin(SSID_WIFI);

  Serial.print("SSID: ");
  Serial.println(SSID_WIFI);
  Serial.print("PSW: ");
  Serial.println(PSW);

  Serial.print("Connecting WLAN ");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println(". Done, device connected.");

  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());

  // Setting the microSD card CS pin as OUTPUT and setting it HIGH
  pinMode(SD_CS, OUTPUT);      
  digitalWrite(SD_CS, HIGH); 
  // Initialize SPI bus for microSD Card
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);
    
  // Initializing the SD card
  if(!SD.begin(SD_CS)){
    Serial.println("Error accessing microSD card!");
    return;
  }else{
      Serial.println("Success accessing microSD card!");
  }

  // Initializes I2S interface for recording
  I2S_Record_Init(); 

  // Register HTTP endpoints
  server.on("/microphone", HTTP_GET, sendWavFile);
  server.on("/sensor", HTTP_GET, sendSensorData);
  server.on("/message_speak", HTTP_POST, speakMessage);

  // Starting the server
  server.enableCORS(true);
  server.begin();
  Serial.println("HTTP Server started");  

  // Setting up I2S 
  audio.setPinout(I2S_BCLK, I2S_LRC, I2S_DOUT);
    
  // Set Volume
  audio.setVolume(8);  
}
 
void loop() {
  // Handle incoming client requests
  server.handleClient();

  // Check if the button is pressed
  int buttonState = digitalRead(BUTTON_PIN);
  float audioDuration;
  
  if (buttonState == LOW) {
    Serial.println("Button pressed");
    
    // Wait for button release and then stop recording
    while (digitalRead(BUTTON_PIN) == LOW) {
      Record_Start(AUDIO_FILE);
    }
    
    if (Record_Available(AUDIO_FILE, &audioDuration)) {
      Serial.print("Recording stopped. Duration: ");
      Serial.print(audioDuration);
      Serial.println(" seconds"); // Debug: Check if audio data is available
      
      // Open the file and Debug: print its size
      File file = SD.open(AUDIO_FILE);
      if (file) {
        Serial.print("File size: ");
        Serial.println(file.size());  // Deve essere maggiore di 44 bytes (header WAV)
        file.close();

      } else {
        Serial.println("ERROR: File not found!");
      }
    }
    
  }

  delay(50);
}

// Function to speak the text in chunks
void speakTextInChunks(String text, int maxLength) {
  int start = 0;
  while (start < text.length()) {
    int end = start + maxLength;

    // Ensure we don't split in the middle of a word
    if (end < text.length()) {
      while (end > start && text[end] != ' ' && text[end] != '.' && text[end] != ',') {
        end--;
      }
    }

    // If no space or punctuation is found, just split at maxLength
    if (end == start) {
      end = start + maxLength;
    }

    String chunk = text.substring(start, end);
    audio.connecttospeech(chunk.c_str(), TTS_GOOGLE_LANGUAGE);

    while (audio.isRunning()) {
      audio.loop();
    }

    start = end + 1;  // Move to the next part, skipping the space
                      // delay(200);       // Small delay between chunks
  }
}

// HTTP endpoint to speak the message
void speakMessage() {
  Serial.print("Argomento: ");
  Serial.println(server.arg("phrasetospeak"));
  if (server.hasArg("phrasetospeak")) {  // Check if "phrasetospeak" parameter exists
        String phrase = server.arg("phrasetospeak");

        Serial.print("Entra nella funzione");
        speakTextInChunks(phrase, 93);
        Serial.println("Message played!");

        server.send(200, "text/plain", "Message played");
  } else {
        server.send(400, "text/plain", "Error with 'phrasetospeak' parameter");
    }
}

// Handle sending temperature & humidity data as JSON
void sendSensorData() {
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    
    if (isnan(h) || isnan(t)) {
        Serial.println("Failed to read from DHT sensor!");
        server.send(400, "text/plain", "Failed to read from DHT sensor!");
        return;
    }

    String jsonResponse = "{\"temperature\": " + String(t) + ", \"humidity\": " + String(h) + "}";
    Serial.println("Sending sensor data: " + jsonResponse);
    server.send(200, "application/json", jsonResponse);
}

// Handle sending the WAV file
void sendWavFile(){
    Serial.println("Sending .wav");
     File wavFile = SD.open(AUDIO_FILE);
    
    if (!wavFile) {
        server.send(404, "text/plain", "File not found");
        return;
    }

    // Set correct content type for WAV files
    server.sendHeader("Content-Type", "audio/wav");
    server.sendHeader("Content-Disposition", "attachment; filename=audio.wav");
    
    // Stream the file
    server.streamFile(wavFile, "audio/wav");
    
    wavFile.close();
    if (SD.exists(AUDIO_FILE)) 
    {  SD.remove(AUDIO_FILE); }
}


