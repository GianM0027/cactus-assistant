from assistantManager import AssistantManager
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

    audio_processing_path = os.path.join("facebook", "wav2vec2-base-960h")
    telegram_bot_token = os.getenv('BOT_TOKEN')
    huggingface_token = os.getenv('CACTUS_TOKEN')
    gemini_token = os.getenv('GEMINI_TOKEN')

    assistant = AssistantManager(audio_processing_path=audio_processing_path,
                                 telegram_bot_token=telegram_bot_token,
                                 gemini_token=gemini_token)
