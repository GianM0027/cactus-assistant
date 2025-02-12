from assistantManager import AssistantManager
import os
from dotenv import load_dotenv

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

    assistant = AssistantManager(audio_processing_path=audio_processing_path,
                                 telegram_bot_token=telegram_bot_token,
                                 gemini_token=gemini_token)