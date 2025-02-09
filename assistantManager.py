import asyncio
import json

import numpy as np
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

        # ID used to identify actions
        self.reminder_action_id = "set_reminder"

        # ID used to identify actors
        self.bot_sender_id = "bot"
        self.cactus_sender_id = "cactus"

        # temporary reminder
        self.reset_new_reminder()

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
            self.bot.reply_to(message, INITIAL_GREETING)

        @self.bot.message_handler(commands=['init_prompt'])
        def set_llm_initialization_prompt(message):
            self._awaiting_init_prompt = True
            self.bot.reply_to(message, ASK_INITIALIZATION_PROMPT)

        @self.bot.message_handler(commands=['username'])
        def set_llm_initialization_prompt(message):
            self._awaiting_user_name = True
            self.bot.reply_to(message, ASK_USERNAME)

        @self.bot.message_handler(commands=['show_reminders'])
        def show_reminders(message):
            user_reminders = self.cactus.get_user_reminders(chat_id=message.chat.id)

            if len(user_reminders) > 0:
                reminders_message = "Here are your reminders:\n"
                for reminder in user_reminders:
                    reminder_date = reminder["date_time"].strftime("%d/%m/%Y %H:%M")
                    reminders_message += f"\n- {reminder['reminder']} - {reminder_date}"
            else:
                reminders_message = "You have no reminders"
            self.bot.reply_to(message, reminders_message)

        @self.bot.message_handler(commands=['delete_reminder'])
        def delete_reminder(message):
            user_reminders = self.cactus.get_user_reminders(chat_id=message.chat.id)
            reminder_choice = "Which reminder do you want to delete?"

            markup = InlineKeyboardMarkup()
            markup.row_width = 1
            markup.add(
                *[InlineKeyboardButton(
                    reminder["reminder"] + " " + reminder["date_time"].strftime("%d/%m/%Y %H:%M"),
                    callback_data="delete_reminder_"+str(reminder["reminder_id"])
                ) for reminder in user_reminders]
            )

            self.bot.send_message(chat_id=message.chat.id, text=reminder_choice, reply_markup=markup)

        @self.bot.message_handler(commands=['voice_preference'])
        def set_voice_preference(message):
            markup = InlineKeyboardMarkup()
            markup.row_width = 1
            options = ["english-male", "english-female", "italian-male", "italian-female"]

            markup.add(
                *[InlineKeyboardButton(option, callback_data="set_voice_preference_"+str(option)) for option in options]
            )

            self.bot.send_message(chat_id=message.chat.id, text="Which one do you prefer?", reply_markup=markup)

        @self.bot.message_handler(commands=['show_init'])
        def set_llm_initialization_prompt(message):
            init_prompt = self.cactus.get_user_initialization_prompt(message.chat.id)

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
            self.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)

            if call.data == "confirm_reminder_yes":
                self.cactus.set_reminder(chat_id=chat_id, reminder=self.new_reminder)
                self.bot.send_message(chat_id, "Reminder confirmed! ✅")
                self._awaiting_user_reminder_confirm = False
                self.reset_new_reminder()

            elif call.data == "confirm_reminder_no":
                self.bot.send_message(chat_id=chat_id, text="Reminder canceled. ❌\n\nHow can I help you?")
                self._awaiting_user_reminder_confirm = False
                self.reset_new_reminder()

            elif call.data.startswith("delete_reminder_"):
                reminder_id = call.data.replace("delete_reminder_", "", 1)
                self.cactus.remove_reminder(chat_id=chat_id, reminder_id=reminder_id)
                self.bot.send_message(chat_id, f"Reminder deleted. 🗑️")

            elif call.data.startswith("set_voice_preference_"):
                language_voice = call.data.replace("set_voice_preference_", "", 1)
                language, voice = language_voice.split("-")
                self.cactus.set_user_language_preference(chat_id=chat_id, language_preference=language)
                self.cactus.set_user_voice_preference(chat_id=chat_id, voice_preference=voice)
                self.bot.send_message(chat_id, f"Voice preference set! 🗣️️")


        @self.bot.message_handler(func=lambda msg: True)
        def handle_message(message):
            # user just entered the new initialization prompt
            if self._awaiting_init_prompt:
                self.cactus.set_user_initialization_prompt(chat_id=message.chat.id, initialization_prompt=message.text)
                self.bot.reply_to(message, INITIALIZATION_PROMPT_CONFIRMATION)
                self._awaiting_init_prompt = False

            # user just entered the new username
            elif self._awaiting_user_name:
                self.cactus.set_user_name(chat_id=message.chat.id, username=message.text)
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

                            self.bot.send_message(chat_id=message.chat.id, text=confirmation_response, reply_markup=markup)
                            self._awaiting_user_reminder_confirm = True

                        else:
                            repeat_message = "Sorry, I did not understand, can you rephrase the request clarifying the date and/or time?"
                            self.bot.reply_to(message, repeat_message)

                # if no action is required, get a response from the LLM
                else:
                    response = self.cactus.get_gemini_response(chat_id=message.chat.id, request=message.text)
                    self.bot.reply_to(message, response)

    ###############################################################################################
    #
    # Cactus/ESP32 methods
    #
    ###############################################################################################
    # todo: implement the function that starts the physical cactus assistant (the ESP) and handles the data
    #  MAURO PUò TOCCARE QUESTE FUNZIONI AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    def run_cactus_assistant(self):
        print("Cactus su uno skateboard!!!")

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
        action_json = self.cactus.get_gemini_response(request=prompt, use_initialization_prompts=False)
        action_dict = json.loads(extract_between_braces(action_json))

        # check if it is required to set a reminder
        reminder_date_time = extract_exact_datetime(action_dict)

        if reminder_date_time is None:
            return None, None
        elif reminder_date_time == "undefined":
            return self.reminder_action_id, {"title": action_dict["content"], "time": "undefined"}
        else:
            return self.reminder_action_id, {"title": action_dict["content"], "time": reminder_date_time}

    def reset_new_reminder(self):
        self.reminder_id = np.random.randint(1000000000)
        self.new_reminder = {"reminder": "", "date_time": None, "chat_id": "", "reminder_id": self.reminder_id}

    async def check_reminders(self):

        # todo, check una volta al mese se ci sono chat inutilizzate e senza reminder, eliminale

        while True:
            now = datetime.now()
            all_reminders = self.cactus.get_all_users_reminders()

            if all_reminders:
                for reminder in all_reminders:
                    reminder_time = reminder["date_time"]

                    if reminder_time and isinstance(reminder_time, str):
                        reminder_time = datetime.fromisoformat(reminder_time)

                    if reminder_time <= now:
                        try:
                            # todo: interazione con il cactus per farlo squillare
                            self.bot.send_message(reminder["chat_id"], f"⏰ Reminder: {reminder['reminder']}")
                        except ApiTelegramException:
                            print(f"Bad Request: chat {reminder['chat_id']} not found")
                        self.cactus.remove_reminder(chat_id=reminder["chat_id"], reminder_id=reminder["reminder_id"])

            await asyncio.sleep(1)