from assistantManager import AssistantManager
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

    audio_processing_path = os.path.join("facebook", "wav2vec2-base-960h")
    telegram_bot_token = os.getenv('BOT_TOKEN')
    huggingface_token = os.getenv('CACTUS_TOKEN')
    # todo: aggiungere flag per decidere se fare chiamate ad HF oppure eseguire LLM in locale

    assistant = AssistantManager(audio_processing_path=audio_processing_path,
                                 telegram_bot_token=telegram_bot_token,
                                 huggingface_token=huggingface_token)
