from assistantManager import AssistantManager
import os
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3

# todo:
#  - SETTARE PROMEMORIA E TIMER (solo da LLM) / VISUALIZZARE (sia da LLLM che da comando) / ELIMINARE (solo da comando)
#  - settare la preferenza sul tono (maschio/femmina - italiano/inglese)
#  - informazioni in tempo reale su umidità e temperatura (con tanto di plot dinamici o fissi)
#  - (OPTIONAL) - caricamento documenti su telegram, LLM che agisce sui documenti

if __name__ == "__main__":
    load_dotenv()

    audio_processing_path = os.path.join("facebook", "wav2vec2-base-960h")
    telegram_bot_token = os.getenv('BOT_TOKEN')
    gemini_token = os.getenv('GEMINI_TOKEN')
    influxdb_client = InfluxDBClient3(host="https://eu-central-1-1.aws.cloud2.influxdata.com",
                                      token=os.environ.get("INFLUXDB_TOKEN"),
                                      org="UniBo")

    assistant = AssistantManager(audio_processing_path=audio_processing_path,
                                 telegram_bot_token=telegram_bot_token,
                                 gemini_token=gemini_token,
                                 influxdb_client=influxdb_client)
