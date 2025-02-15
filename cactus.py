import os

from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch
import librosa
from cactus_memory import CactusMemory
import google.generativeai as genai
from prompts_and_constants import *
from deepgram import DeepgramClient, PrerecordedOptions, FileSource

class Cactus:
    def __init__(self, gemini_token, deepgram_token):
        self.gemini_token = gemini_token
        self.deepgram_token = deepgram_token
        self.cactus_memory = CactusMemory()

    def set_user_initialization_prompt(self, initialization_prompt):
        self.cactus_memory.set_user_initialization_prompt(prompt=initialization_prompt)

    def get_user_reminders(self):
        return self.cactus_memory.get_user_reminders()

    def get_user_timers(self):
        return self.cactus_memory.get_user_timers()

    def remove_reminder(self, reminder_id):
        users_data = self.cactus_memory.get_user_data()
        for reminder in users_data[self.cactus_memory.user_reminders_key]:
            if str(reminder["reminder_id"]) == str(reminder_id):
                users_data[self.cactus_memory.user_reminders_key].remove(reminder)
                break
        self.cactus_memory.save_to_memory(users_data)

    def remove_timer(self, timer_id):
        users_data = self.cactus_memory.get_user_data()
        for timer in users_data[self.cactus_memory.user_timers_key]:
            if str(timer["timer_id"]) == str(timer_id):
                users_data[self.cactus_memory.user_timers_key].remove(timer)
                break
        self.cactus_memory.save_to_memory(users_data)

    def set_chat_id(self, chat_id):
        self.cactus_memory.set_chat_id(chat_id=chat_id)

    def set_reminder(self, reminder):
        self.cactus_memory.set_reminder(reminder=reminder)

    def set_timer(self, timer):
        self.cactus_memory.set_timer(timer=timer)

    def set_user_name(self, username):
        self.cactus_memory.set_user_name(name=username)

    def get_user_initialization_prompt(self):
        return self.cactus_memory.get_user_initialization_prompt()

    def get_user_name(self):
        return self.cactus_memory.get_user_name()

    def get_user_voice_preference(self):
        return self.cactus_memory.get_user_voice_preference()

    def get_user_chat_id(self):
        return self.cactus_memory.get_user_chat_id()

    def get_user_language_preference(self):
        return self.cactus_memory.get_user_language_preference()

    def set_user_voice_preference(self, voice_preference):
        return self.cactus_memory.set_user_voice_preference(voice_preference=voice_preference)

    def set_user_language_preference(self, language_preference):
        return self.cactus_memory.set_user_language_preference(language_preference=language_preference)

    def get_string_user_info(self):
        user_name = self.cactus_memory.get_user_name()
        user_initialization_prompt = self.cactus_memory.get_user_initialization_prompt()
        reminders = self.cactus_memory.get_user_reminders()
        timers = self.cactus_memory.get_user_reminders()

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

    def speech_to_text(self, audio):
        try:
            # STEP 1 Create a Deepgram client using the API key
            deepgram = DeepgramClient(api_key=self.deepgram_token)

            payload: FileSource = {
                "buffer": audio,
            }

            # STEP 2: Configure Deepgram options for audio analysis
            options = PrerecordedOptions(
                model="nova-3",
                smart_format=True,
            )

            # STEP 3: Call the transcribe_file method with the text payload and options
            response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
            return response["results"]["channels"][0]["alternatives"][0]["transcript"]

        except Exception as e:
            print(f"Exception: {e}")

