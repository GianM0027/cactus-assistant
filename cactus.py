from huggingface_hub import InferenceClient
import os
import requests
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch
import librosa
from gtts import gTTS
from cactus_memory import CactusMemory


class Cactus:
    def __init__(self, audio_processing_path):
        self.audio_processor = Wav2Vec2Processor.from_pretrained(audio_processing_path)
        self.audio_model = Wav2Vec2ForCTC.from_pretrained(audio_processing_path)
        self.memory = CactusMemory()

    def get_gemma_response(self, prompt):
        API_URL = "https://api-inference.huggingface.co/models/google/gemma-2-9b-it"
        headers = {"Authorization": f"Bearer {os.getenv('CACTUS_TOKEN')}"}

        payload = {"inputs": prompt}
        response = requests.post(API_URL, headers=headers, json=payload)
        data = response.json()

        try:
            generated_text = data[0]["generated_text"]
        except KeyError:
            generated_text = data.get("error", "Unable to retrieve an answer")

        response_text = generated_text.split(prompt)[-1]

        return response_text

    def get_inference_client_response(self, prompt, token):
        client = InferenceClient(api_key=token)

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        completion = client.chat.completions.create(
            model="Qwen/QwQ-32B-Preview",
            messages=messages,
            max_tokens=1024
        )

        return completion.choices[0].message.content

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
