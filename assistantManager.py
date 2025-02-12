import asyncio
import json
import time

import numpy as np
import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from cactus import Cactus
from prompts_and_constants import *
from utils import *
from datetime import datetime
import threading


# todo: ricontrolla tempo dei reminder e dei timer, li imposta in maniera errata (timer aggiustato, check reminder)

class AssistantManager:
    def __init__(self, audio_processing_path, telegram_bot_token, gemini_token):
        self.bot = telebot.TeleBot(telegram_bot_token)
        self.cactus = Cactus(audio_processing_path=audio_processing_path, gemini_token=gemini_token)
        self.gemini_token = gemini_token

        # awaiting tags, to set when the telegram bot need to wait an answer from the user
        self._awaiting_user_name = False
        self._awaiting_init_prompt = False
        self._awaiting_user_reminder_confirm = False

        # temporary reminder
        self.reset_new_reminder()

        # run assistant
        self.setup_bot_handlers()
        self._run_assistant()

    def _run_assistant(self):
        bot_thread = threading.Thread(target=self.bot.infinity_polling, daemon=True)
        bot_thread.start()
        asyncio.run(self.check_timers_and_reminders())

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

        @self.bot.message_handler(commands=['show_timers'])
        def show_timers(message):
            user_timers = self.cactus.get_user_timers(chat_id=message.chat.id)

            if len(user_timers) > 0:
                timers_message = "Here are your reminders:\n"
                for timer in user_timers:
                    timer_date = timer["date_time"].strftime("%d/%m/%Y %H:%M")
                    timers_message += f"\n- {timer_date}"
            else:
                timers_message = "You have no reminders"
            self.bot.reply_to(message, timers_message)

        @self.bot.message_handler(commands=['delete_reminder'])
        def delete_reminder(message):
            user_reminders = self.cactus.get_user_reminders(chat_id=message.chat.id)
            reminder_choice = "Which reminder do you want to delete?"

            markup = InlineKeyboardMarkup()
            markup.row_width = 1
            markup.add(
                *[InlineKeyboardButton(
                    reminder["reminder"] + " " + reminder["date_time"].strftime("%d/%m/%Y %H:%M"),
                    callback_data="delete_reminder_" + str(reminder["reminder_id"])
                ) for reminder in user_reminders]
            )

            self.bot.send_message(chat_id=message.chat.id, text=reminder_choice, reply_markup=markup)

        @self.bot.message_handler(commands=['delete_timer'])
        def delete_timer(message):
            user_timers = self.cactus.get_user_timers(chat_id=message.chat.id)
            timer_choice = "Which timer do you want to delete?"

            markup = InlineKeyboardMarkup()
            markup.row_width = 1
            markup.add(
                *[InlineKeyboardButton(
                    timer["date_time"].strftime("%d/%m/%Y %H:%M"),
                    callback_data="delete_timer_" + str(timer["timer_id"])
                ) for timer in user_timers]
            )

            self.bot.send_message(chat_id=message.chat.id, text=timer_choice, reply_markup=markup)

        @self.bot.message_handler(commands=['voice_preference'])
        def set_voice_preference(message):
            markup = InlineKeyboardMarkup()
            markup.row_width = 1
            options = ["english-male", "english-female", "italian-male", "italian-female"]

            markup.add(
                *[InlineKeyboardButton(option, callback_data="set_voice_preference_" + str(option)) for option in
                  options]
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
                self.bot.reply_to(message,
                                  f"You did not set an initialization prompt. You can do so with the command \\init_prompt")

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
                self.bot.send_message(chat_id=chat_id, text="Reminder canceled. ❌")
                self._awaiting_user_reminder_confirm = False
                self.reset_new_reminder()

            elif call.data.startswith("delete_reminder_"):
                reminder_id = call.data.replace("delete_reminder_", "", 1)
                self.cactus.remove_reminder(chat_id=chat_id, reminder_id=reminder_id)
                self.bot.send_message(chat_id, f"Reminder deleted. 🗑️")

            elif call.data.startswith("delete_timer_"):
                timer_id = call.data.replace("delete_timer_", "", 1)
                self.cactus.remove_timer(chat_id=chat_id, timer_id=timer_id)
                self.bot.send_message(chat_id, f"Timer deleted. 🗑️")

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
                action_id = self.action_is_required(request=message.text)

                # user asked to set reminder
                if REMINDER_ACTION_ID in action_id:
                    self.ask_reminder_confirmation(message.text, message.chat.id)

                # user asked to set timer
                elif TIMER_ACTION_ID in action_id:
                    self.set_timer(message.text, message.chat.id)

                else:
                    username = self.cactus.get_user_name(chat_id=message.chat.id)
                    user_init_prompt = self.cactus.get_user_initialization_prompt(message.chat.id)
                    intro_to_user_message = "\n\n## USER MESSAGE:\n"

                    # user asked for information about its data
                    if USER_INFO_ID in action_id:
                        system_initialization_prompt = get_cactus_base_instructions_short(sender=BOT_SENDER_ID,
                                                                                          user_name=username,
                                                                                          user_initialization_prompt=user_init_prompt)
                        user_info = self.cactus.get_string_user_info(message.chat.id)
                        init_prompt = system_initialization_prompt + user_info + intro_to_user_message
                        llm_response = self.cactus.get_gemini_response(request=message.text,
                                                                       initialization_prompt=init_prompt)
                        self.bot.send_message(message.chat.id, llm_response)

                    # no action required
                    elif NO_ACTION_REQUIRED_ID in action_id:
                        system_initialization_prompt = get_cactus_base_instructions(sender=BOT_SENDER_ID,
                                                                                    user_name=username,
                                                                                    user_initialization_prompt=user_init_prompt)
                        init_prompt = system_initialization_prompt + intro_to_user_message
                        llm_response = self.cactus.get_gemini_response(request=message.text,
                                                                       initialization_prompt=init_prompt)

                        self.bot.send_message(message.chat.id, llm_response)

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
    def action_is_required(self, request):
        user_request_intro = "\n---\nUSER MESSAGE:\n"
        llm_answer = self.cactus.get_gemini_response(request=request,
                                                     initialization_prompt=CHECK_ACTION_IS_REQUIRED_PROMPT + user_request_intro)

        return llm_answer

    def reset_new_reminder(self):
        self.reminder_id = np.random.randint(1000000000)
        self.new_reminder = {"reminder": "", "date_time": None, "chat_id": "", "reminder_id": self.reminder_id}

    def ask_reminder_confirmation(self, request, chat_id):
        llm_response = self.cactus.get_gemini_response(request=get_reminder_check_prompt(request),
                                                       initialization_prompt="")
        action_dict = json.loads(extract_between_braces(llm_response))
        reminder_date_time = extract_exact_datetime(action_dict, bot=self.bot, chat_id=chat_id) # todo: also takes bot and chat_id and send message to user if something wrong
        reminder_title = action_dict["content"]
        if reminder_date_time:
            confirmation_response = f"{reminder_title}. " + format_datetime_natural(reminder_date_time)

            markup = InlineKeyboardMarkup()
            markup.row_width = 2
            markup.add(
                InlineKeyboardButton("Yes", callback_data="confirm_reminder_yes"),
                InlineKeyboardButton("No", callback_data="confirm_reminder_no")
            )

            self.new_reminder["reminder"] = reminder_title
            self.new_reminder["date_time"] = reminder_date_time
            self.new_reminder["chat_id"] = chat_id

            self.bot.send_message(chat_id=chat_id, text=confirmation_response,
                                  reply_markup=markup)
            self._awaiting_user_reminder_confirm = True

        else:
            repeat_message = "Sorry, I did not understand, can you rephrase the request clarifying the date and/or time?"
            self.bot.send_message(chat_id, repeat_message)

    def set_timer(self, request, chat_id):
        llm_response = self.cactus.get_gemini_response(request=get_timer_set_prompt(request),
                                                       initialization_prompt="")
        action_dict = json.loads(extract_between_braces(llm_response))
        timer_date_time = extract_exact_datetime(action_dict)

        if timer_date_time:
            timer_id = len(self.cactus.get_user_timers(chat_id))+1
            new_timer = {"date_time": timer_date_time, "chat_id": chat_id, "timer_id": timer_id}
            self.cactus.set_timer(chat_id=chat_id, timer=new_timer)

            # Send confirmation message
            self.bot.send_message(chat_id, f"{parse_time_delay(timer_date_time)} timer confirmed! ✅")
        else:
            repeat_message = "Sorry, I did not understand, can you rephrase the request clarifying the time?"
            self.bot.send_message(chat_id, repeat_message)

    async def check_timers_and_reminders(self):

        # todo, check una volta al mese se ci sono chat inutilizzate e senza reminder, eliminale

        while True:
            now = datetime.now()
            all_reminders = self.cactus.get_all_users_reminders()
            all_timers = self.cactus.get_all_users_timers()

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

            if all_timers:
                for timer in all_timers:
                    timer_time = timer["date_time"]

                    if timer_time and isinstance(timer_time, str):
                        timer_time = datetime.fromisoformat(timer_time)
                    if timer_time <= now:
                        try:
                            # todo: interazione con il cactus per farlo squillare
                            self.bot.send_message(timer["chat_id"], f"⏰ Time's up! ⏰")
                        except ApiTelegramException:
                            print(f"Bad Request: chat {timer['chat_id']} not found")
                        self.cactus.remove_timer(chat_id=timer["chat_id"], timer_id=timer["timer_id"])

            await asyncio.sleep(1)
