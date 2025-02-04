import json
import telebot
from cactus import Cactus
from prompts import *

class AssistantManager:
    def __init__(self, audio_processing_path, telegram_bot_token, gemini_token):
        self.bot = telebot.TeleBot(telegram_bot_token)
        self.cactus = Cactus(audio_processing_path=audio_processing_path, gemini_token=gemini_token)
        self.gemini_token = gemini_token

        self._awaiting_user_name = False
        self._awaiting_init_prompt = False

        self.setup_bot_handlers()
        self._run_assistant()

    def _run_assistant(self):
        self.bot.infinity_polling()
        self.run_cactus_assistant()

    ###############################################################################################
    #
    # Telegram Bot methods
    #
    ###############################################################################################
    def setup_bot_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            self.bot.reply_to(message, INITIAL_GREETING)
            self._awaiting_user_name = True

        @self.bot.message_handler(commands=['init_prompt'])
        def set_llm_initialization_prompt(message):
            self._awaiting_init_prompt = True
            self.bot.reply_to(message, ASK_INITIALIZATION_PROMPT)

        @self.bot.message_handler(commands=['username'])
        def set_llm_initialization_prompt(message):
            self._awaiting_user_name = True
            self.bot.reply_to(message, ASK_USERNAME)

        # todo: funzione che mostra l'initialization prompt attualmente in uso
        @self.bot.message_handler(commands=['show_init'])
        def set_llm_initialization_prompt(message):
            init_prompt = self.cactus.memory.user_initialization_prompt

            if init_prompt != "":
                pre = "Your current initialization prompt is:\n\n"
                post = "\n\nIs there something else I can do for you?"

                self.bot.reply_to(message, pre + init_prompt + post)

            else:
                self.bot.reply_to(message, f"You did not set an initialization prompt. You can do so with the command \\init_prompt")

        @self.bot.message_handler(func=lambda msg: True)
        def handle_message(message):

            # user just entered the new initialization prompt
            if self._awaiting_init_prompt:
                self.cactus.memory.set_user_initialization_prompt(message.text)
                self.bot.reply_to(message, INITIALIZATION_PROMPT_CONFIRMATION)
                self._awaiting_init_prompt = False

            # user just entered the new username
            elif self._awaiting_user_name:
                self.cactus.memory.set_user_name(message.text)
                self.bot.reply_to(message, f"Thanks {message.text}! " + USERNAME_CONFIRMATION)
                self._awaiting_user_name = False

            # user is sending a new message
            else:
                response = self.cactus.get_gemini_response(message.text)
                self.bot.reply_to(message, response)

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