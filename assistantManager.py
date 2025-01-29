import json
import telebot
from cactus import Cactus
from prompts import *

class AssistantManager:
    def __init__(self, audio_processing_path, telegram_bot_token, huggingface_token):
        self.bot = telebot.TeleBot(telegram_bot_token)
        self.cactus_assistant = Cactus(audio_processing_path=audio_processing_path)
        self.hf_token = huggingface_token

        self._run_assistant()

    def _run_assistant(self):
        self.run_telegram_bot()
        self.run_cactus_assistant()

    ###############################################################################################
    #
    # Telegram Bot methods
    #
    ###############################################################################################
    def setup_bot_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            # todo: come primo messaggio chiedi nome dell'utente e salvalo in memoria
            self.bot.reply_to(message, INITIAL_GREETING)

        @self.bot.message_handler(commands=['hf_api'])
        def set_hf_token_api(message):
            return "Functionality to implement"

        @self.bot.message_handler(commands=['init_prompt'])
        def set_llm_initialization_prompt(message):
            return "Functionality to implement"

        @self.bot.message_handler(func=lambda msg: True)
        def handle_message(message):
            self.bot.reply_to(message, self.cactus_assistant.get_inference_client_response(message.text, self.hf_token))

    def run_telegram_bot(self):
        self.setup_bot_handlers()
        self.bot.infinity_polling()

    ###############################################################################################
    #
    # Cactus/ESP32 methods
    #
    ###############################################################################################

    # todo: implement the function that starts the physical cactus assistant (the ESP) and handles the data
    #  MAURO PUò TOCCARE QUESTE FUNZIONI AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    def run_cactus_assistant(self):
        pass

    def mau_decidi_tu_la_logica_di_queste_funzioni_che_fanno_https_con_ESP(self):
        pass

    ###############################################################################################
    #
    # Utils methods
    #
    ###############################################################################################

    # todo: implement the function that given a user request decides what to do with it (send to cactus VS perform action)
    def action_is_required(self, request):
        pass