# Cactus - Personal Desk Assistant

Cactus is an AI-powered desk assistant that integrates a physical IoT device with a Telegram bot, providing a multi-platform interaction experience. The assistant can process voice and text commands to manage reminders, timers, environmental data, and user settings. It uses an ESP32 microcontroller for hardware control and APIs for advanced natural language processing.

## Features

- **Voice & Text Interaction**: Users can interact with Cactus via a microphone or Telegram bot.
- **Task Management**: Supports reminders and timers with automatic notifications.
- **Environmental Monitoring**: Collects real-time temperature and humidity data.
- **Adaptive AI Responses**: Utilizes an LLM to process and respond to user requests dynamically.
- **Customizable User Settings**: Users can define their assistant's behavior via initialization prompts and preferences.
- **3D-Printed Enclosure**: A custom-printed case shaped like a cactus to house the hardware.

## Architecture

The system is composed of both **hardware** and **software** components:

### Hardware
- ESP32 microcontroller
- I2S microphone for audio input
- MAX98357A I2S amplifier and speaker for audio output
- DHT11 sensor for temperature and humidity monitoring
- MicroSD card module for audio storage
- Physical button for user interaction
<img src="https://github.com/user-attachments/assets/adc50826-a83a-4772-ba23-3c014e679aeb" width="400">
<img src="https://github.com/user-attachments/assets/21e73ee1-8eaf-47b8-ac18-37fe0c55611f" width="400">


### Software
- **ESP32 Firmware**: Handles sensor readings, audio recording, and HTTP requests.
- **Python Client**: Processes audio files, manages interactions with the LLM, and handles data storage.
- **Telegram Bot**: Provides a chat interface for interaction, notifications, and data retrieval.
<img src="https://github.com/user-attachments/assets/eef28c7e-2dda-4bfc-a4db-63734bd1e54e" width="400">

For a comprehensive explanation of the system, its implementation, and additional details, refer to the **IoT_Report.pdf** included in this repository.
