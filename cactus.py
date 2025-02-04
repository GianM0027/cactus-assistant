from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch
import librosa
from gtts import gTTS
from cactus_memory import CactusMemory
import google.generativeai as genai
from prompts import *


class Cactus:
    def __init__(self, audio_processing_path, gemini_token):
        self.gemini_token = gemini_token
        self.audio_processor = Wav2Vec2Processor.from_pretrained(audio_processing_path)
        self.audio_model = Wav2Vec2ForCTC.from_pretrained(audio_processing_path)
        self.memory = CactusMemory()

    def get_gemini_response(self, request):
        genai.configure(api_key=self.gemini_token)
        model = genai.GenerativeModel("gemini-1.5-flash")

        if self.memory.user_name != "":
            username_info = f"The user name is {self.memory.user_name}"
        else:
            username_info = ""

        prompt = CACTUS_BASE_INSTRUCTIONS + username_info + self.memory.user_initialization_prompt + request

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

    def from_text_to_audio(self, text):
        audio_mp3 = gTTS(text=text, lang="en", slow=False)
        return audio_mp3
