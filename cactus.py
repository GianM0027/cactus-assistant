from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch
import librosa
from cactus_memory import CactusMemory
import google.generativeai as genai
from prompts import *

class Cactus:
    def __init__(self, audio_processing_path, gemini_token):
        self.gemini_token = gemini_token
        self.audio_processor = Wav2Vec2Processor.from_pretrained(audio_processing_path)
        self.audio_model = Wav2Vec2ForCTC.from_pretrained(audio_processing_path)
        self.cactus_memory = CactusMemory()

    def set_user_initialization_prompt(self, chat_id, initialization_prompt):
        self.cactus_memory.set_user_initialization_prompt(chat_id=chat_id, prompt=initialization_prompt)

    def get_user_reminders(self, chat_id):
        return self.cactus_memory.get_user_reminders(chat_id)

    def get_all_users_reminders(self):
        users_reminders = []
        users_data = self.cactus_memory.get_all_users_data()
        for id, data in users_data.items():
            for reminder in data["user_reminders"]:
                users_reminders.append(reminder)
        return users_reminders

    def remove_reminder(self, chat_id, reminder_id):
        users_data = self.cactus_memory.get_user_data(chat_id=chat_id)
        for reminder in users_data["user_reminders"]:
            if str(reminder["reminder_id"]) == str(reminder_id):
                users_data["user_reminders"].remove(reminder)
                break
        self.cactus_memory.save_to_memory(chat_id, users_data)

    def set_reminder(self, chat_id, reminder):
        self.cactus_memory.set_reminder(chat_id=chat_id, reminder=reminder)

    def set_user_name(self, chat_id, username):
        self.cactus_memory.set_user_name(chat_id=chat_id, name=username)

    def get_user_initialization_prompt(self, chat_id):
        return self.cactus_memory.get_user_initialization_prompt(chat_id)

    def get_user_name(self, chat_id):
        return self.cactus_memory.get_user_name(chat_id)

    def get_user_voice_preference(self, chat_id):
        return self.cactus_memory.get_user_voice_preference(chat_id=chat_id)

    def get_user_language_preference(self, chat_id):
        return self.cactus_memory.get_user_language_preference(chat_id=chat_id)

    def set_user_voice_preference(self, chat_id, voice_preference):
        return self.cactus_memory.set_user_voice_preference(chat_id=chat_id, voice_preference=voice_preference)

    def set_user_language_preference(self, chat_id, language_preference):
        return self.cactus_memory.set_user_language_preference(chat_id=chat_id, language_preference=language_preference)

    def get_gemini_response(self, request, chat_id=None, use_initialization_prompts=True):
        genai.configure(api_key=self.gemini_token)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Warning for Developer
        if use_initialization_prompts and chat_id is None:
            print("WARNING! Gemini (get_gemini_response) is not able to access the user data. Set 'chat_id'")

        if use_initialization_prompts and chat_id:
            username = self.cactus_memory.get_user_name(chat_id)
            user_init_prompt = self.cactus_memory.get_user_initialization_prompt(chat_id)
            username_info = f"The user name is {username}. " if username else ""
            prompt = CACTUS_BASE_INSTRUCTIONS + username_info + user_init_prompt + request
        else:
            prompt = request

        response = model.generate_content(prompt)
        return response.text

    def from_audio_to_text(self, audio_path):
        audio, sample_rate = librosa.load(audio_path, sr=16000)
        inputs = self.audio_processor(audio, sampling_rate=sample_rate, return_tensors="pt", padding=True)

        with torch.no_grad():
            logits = self.audio_model(**inputs).logits

        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.audio_processor.batch_decode(predicted_ids, skip_special_tokens=True)
        return transcription[0]
