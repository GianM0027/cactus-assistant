from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch
import librosa
from cactus_memory import CactusMemory
import google.generativeai as genai
from prompts_and_constants import *

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

    def get_user_timers(self, chat_id):
        return self.cactus_memory.get_user_timers(chat_id)

    def get_all_users_reminders(self):
        users_reminders = []
        users_data = self.cactus_memory.get_all_users_data()
        for id, data in users_data.items():
            for reminder in data[self.cactus_memory.user_reminders_key]:
                users_reminders.append(reminder)
        return users_reminders

    def remove_reminder(self, chat_id, reminder_id):
        users_data = self.cactus_memory.get_user_data(chat_id=chat_id)
        for reminder in users_data[self.cactus_memory.user_reminders_key]:
            if str(reminder["reminder_id"]) == str(reminder_id):
                users_data[self.cactus_memory.user_reminders_key].remove(reminder)
                break
        self.cactus_memory.save_to_memory(chat_id, users_data)

    def remove_timer(self, chat_id, timer_id):
        users_data = self.cactus_memory.get_user_data(chat_id=chat_id)
        for timer in users_data[self.cactus_memory.user_timers_key]:
            if str(timer["timer_id"]) == str(timer_id):
                users_data[self.cactus_memory.user_timers_key].remove(timer)
                break
        self.cactus_memory.save_to_memory(chat_id, users_data)

    def get_all_users_timers(self):
        users_timers = []
        users_data = self.cactus_memory.get_all_users_data()
        for id, data in users_data.items():
            for timer in data[self.cactus_memory.user_timers_key]:
                users_timers.append(timer)
        return users_timers

    def set_reminder(self, chat_id, reminder):
        self.cactus_memory.set_reminder(chat_id=chat_id, reminder=reminder)

    def set_timer(self, chat_id, timer):
        self.cactus_memory.set_timer(chat_id=chat_id, timer=timer)

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

    def get_string_user_info(self, chat_id):
        user_name = self.cactus_memory.get_user_name(chat_id)
        user_initialization_prompt = self.cactus_memory.get_user_initialization_prompt(chat_id=chat_id)
        reminders = self.cactus_memory.get_user_reminders(chat_id)
        timers = self.cactus_memory.get_user_reminders(chat_id)

        intro_prompt = "USER INFORMATION: "

        user_name_prompt = f"\n- The user set an username: {user_name}." if user_name else \
            "\n- The user did not set a username. This action can be performed on the telegram bot."

        init_prompt = f"\n- The user set an initialization prompt: '{user_initialization_prompt}'" if user_initialization_prompt else \
            "\n- The user did not set an initialization prompt for the system. This action can be performed on the telegram bot."

        reminders_prompt = f"\n- The user has the following active reminders: {str(reminders)}" if reminders else \
            "\n- The user doesn't have any active reminders set. This can be set from bot the telegram bot or speaking to the cactus."

        timers_prompt = f"\n- The user has the following active timers: {str(timers)}" if timers else \
            "\n- The user doesn't have any active timers set. This can be set from bot the telegram bot or speaking to the cactus."

        optional_info = user_name_prompt + init_prompt + reminders_prompt + timers_prompt

        return intro_prompt + optional_info


    def get_gemini_response(self, request, initialization_prompt=""):
        genai.configure(api_key=self.gemini_token)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(initialization_prompt+request)
        return response.text

    def from_audio_to_text(self, audio_path):
        audio, sample_rate = librosa.load(audio_path, sr=16000)
        inputs = self.audio_processor(audio, sampling_rate=sample_rate, return_tensors="pt", padding=True)

        with torch.no_grad():
            logits = self.audio_model(**inputs).logits

        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.audio_processor.batch_decode(predicted_ids, skip_special_tokens=True)
        return transcription[0]
