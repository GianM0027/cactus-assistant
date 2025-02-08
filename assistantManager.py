import asyncio
import json
import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from cactus import Cactus
from prompts import *
from utils import *
from datetime import datetime
import threading

class AssistantManager:
    def __init__(self, audio_processing_path, telegram_bot_token, gemini_token):
        self.bot = telebot.TeleBot(telegram_bot_token)
        self.cactus = Cactus(audio_processing_path=audio_processing_path, gemini_token=gemini_token)
        self.gemini_token = gemini_token

        # awaiting tags, to set when the telegram bot need to wait an answer from the user
        self._awaiting_user_name = False
        self._awaiting_init_prompt = False
        self._awaiting_user_reminder_confirm = False

        # ID used to identify chat
        self.chat_id = None

        # ID used to identify actions
        self.reminder_action_id = "set_reminder"

        # ID used to identify actors
        self.bot_sender_id = "bot"
        self.cactus_sender_id = "cactus"

        # reminder list
        self.reset_new_reminder()
        self.reminder_list = []

        # run assistant
        self.setup_bot_handlers()
        self._run_assistant()

    def _run_assistant(self):
        bot_thread = threading.Thread(target=self.bot.infinity_polling, daemon=True)
        bot_thread.start()
        asyncio.run(self.check_reminders())

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
            self.chat_id = message.chat.id
            self.cactus.set_chat_id(self.chat_id)
            self.bot.reply_to(message, INITIAL_GREETING)

        @self.bot.message_handler(commands=['init_prompt'])
        def set_llm_initialization_prompt(message):
            self._awaiting_init_prompt = True
            self.bot.reply_to(message, ASK_INITIALIZATION_PROMPT)

        @self.bot.message_handler(commands=['username'])
        def set_llm_initialization_prompt(message):
            self._awaiting_user_name = True
            self.bot.reply_to(message, ASK_USERNAME)

        @self.bot.message_handler(commands=['show_init'])
        def set_llm_initialization_prompt(message):
            init_prompt = self.cactus.get_user_initialization_prompt()

            if init_prompt != "":
                pre = "Your current initialization prompt is:\n\n"
                post = "\n\nIs there something else I can do for you?"

                self.bot.reply_to(message, pre + init_prompt + post)

            else:
                self.bot.reply_to(message, f"You did not set an initialization prompt. You can do so with the command \\init_prompt")

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            chat_id = call.message.chat.id
            message_id = call.message.message_id

            # Remove buttons by editing the message and setting reply_markup=None
            self.bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)

            if call.data == "confirm_reminder_yes":
                self.reminder_list.append(self.new_reminder)
                self.bot.send_message(chat_id, "Reminder confirmed! ✅")
                self._awaiting_user_reminder_confirm = False
            elif call.data == "confirm_reminder_no":
                self.bot.send_message(chat_id, "Reminder canceled. ❌\n\nHow can I help you?")
                self._awaiting_user_reminder_confirm = False

            self.reset_new_reminder()

        @self.bot.message_handler(func=lambda msg: True)
        def handle_message(message):
            print("CHAT ID by message: ", message.chat.id)
            print("self.chat_id: ", self.chat_id)

            # user just entered the new initialization prompt
            if self._awaiting_init_prompt:
                self.cactus.set_user_initialization_prompt(message.text)
                self.bot.reply_to(message, INITIALIZATION_PROMPT_CONFIRMATION)
                self._awaiting_init_prompt = False

            # user just entered the new username
            elif self._awaiting_user_name:
                self.cactus.set_user_name(message.text)
                self.bot.reply_to(message, f"Thanks {message.text}! " + USERNAME_CONFIRMATION)
                self._awaiting_user_name = False

            # user is sending a new message
            else:

                # check if an action is required
                action_id, action_specific = self.action_is_required(message.text)
                if action_id is not None:
                    if action_id == self.reminder_action_id:
                        reminder_title = action_specific["title"]
                        reminder_date = action_specific["time"]

                        if reminder_date != "undefined":
                            confirmation_response = f"{reminder_title}. " + format_datetime_natural(reminder_date)

                            markup = InlineKeyboardMarkup()
                            markup.row_width = 2
                            markup.add(
                                InlineKeyboardButton("Yes", callback_data="confirm_reminder_yes"),
                                InlineKeyboardButton("No", callback_data="confirm_reminder_no")
                            )

                            self.new_reminder["reminder"] = reminder_title
                            self.new_reminder["date_time"] = reminder_date
                            self.new_reminder["chat_id"] = message.chat.id

                            self.bot.send_message(message.chat.id, confirmation_response, reply_markup=markup)
                            self._awaiting_user_reminder_confirm = True
                        else:
                            repeat_message = "Sorry, I did not understand, can you rephrase the request clarifying the date and/or time?"
                            self.bot.reply_to(message, repeat_message)

                # if no action is required, get a response from the LLM
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
    # Action Performer
    #
    ###############################################################################################
    # todo: implement the function that given a user request decides what to do with it (send to cactus VS perform action)
    def action_is_required(self, request):
        prompt = get_reminder_check_prompt() + "\n---\n" + "User request is:\n" + request
        action_json = self.cactus.get_gemini_response(prompt, use_initialization_prompts=False)
        action_dict = json.loads(extract_between_braces(action_json))

        print(action_dict)

        # check if it is required to set a reminder
        reminder_date_time = extract_exact_datetime(action_dict)

        if reminder_date_time is None:
            return None, None
        elif reminder_date_time == "undefined":
            return self.reminder_action_id, {"title": action_dict["content"], "time": "undefined"}
        else:
            return self.reminder_action_id, {"title": action_dict["content"], "time": reminder_date_time}

    def perform_action(self, action_ID, action_specific, sender):
        if action_ID == self.reminder_action_id:
            self.set_reminder(action_specific)
        # todo: other actions

    def set_reminder(self, json_file):
        pass

    def reset_new_reminder(self):
        self.new_reminder = {"reminder": "", "date_time": None, "chat_id": ""}

    async def check_reminders(self):
        while True:
            now = datetime.now()
            for reminder in self.reminder_list[:]:
                reminder_time = reminder["date_time"]

                if reminder_time and isinstance(reminder_time, str):
                    reminder_time = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M:%S")

                if reminder_time <= now:
                    try:
                        self.bot.send_message(reminder["chat_id"], f"⏰ Reminder: {reminder['reminder']}")
                    except ApiTelegramException:
                        print(f"Bad Request: chat {reminder['chat_id']} not found")
                    self.reminder_list.remove(reminder)

            await asyncio.sleep(1)