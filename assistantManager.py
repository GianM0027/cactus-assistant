import asyncio
import json
import os
import time
import requests

import numpy as np
import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from cactus import Cactus
from prompts_and_constants import *
from utils import *
from datetime import datetime
import threading
from influxdb_client_3 import Point
import matplotlib.pyplot as plt
import pandas as pd
import io


class AssistantManager:
    def __init__(self, deepgram_token, telegram_bot_token, gemini_token, influxdb_client):
        self.bot = telebot.TeleBot(telegram_bot_token)
        self.cactus = Cactus(gemini_token=gemini_token, deepgram_token=deepgram_token)
        self.influxdb_client = influxdb_client

        # awaiting tags, to set when the telegram bot need to wait an answer from the user
        self._awaiting_user_name = False
        self._awaiting_init_prompt = False
        self._awaiting_temperature_plot = False
        self._awaiting_humidity_plot = False

        # run assistant
        self.setup_bot_handlers()
        self._run_assistant()

    def _run_assistant(self):
        # Start the bot in a separate thread
        bot_thread = threading.Thread(target=self.bot.infinity_polling, daemon=True)
        bot_thread.start()

        # Run all async tasks in an event loop
        async def run_tasks():
            await asyncio.gather(
                self.check_timers_and_reminders(),
                self.get_sensor_data(),
                self.monitor_mic_registration()
            )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_tasks())

    ###############################################################################################
    #
    # Telegram Bot methods
    #
    ###############################################################################################
    def setup_bot_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            self.bot.send_message(message.chat.id, INITIAL_GREETING)
            self.cactus.set_chat_id(message.chat.id)

        @self.bot.message_handler(commands=['init_prompt'])
        def set_llm_initialization_prompt(message):
            self._awaiting_init_prompt = True
            self.bot.send_message(message.chat.id, ASK_INITIALIZATION_PROMPT)

        @self.bot.message_handler(commands=['username'])
        def set_llm_initialization_prompt(message):
            self._awaiting_user_name = True
            self.bot.send_message(message.chat.id, ASK_USERNAME)

        @self.bot.message_handler(commands=['show_reminders'])
        def show_reminders(message):
            user_reminders = self.cactus.get_user_reminders()

            if len(user_reminders) > 0:
                reminders_message = "Here are your reminders:\n"
                for reminder in user_reminders:
                    reminder_date = reminder["date_time"].strftime("%d/%m/%Y %H:%M")
                    reminders_message += f"\n- {reminder['reminder']} - {reminder_date}"
            else:
                reminders_message = "You have no reminders"
            self.bot.send_message(message.chat.id, reminders_message)

        @self.bot.message_handler(commands=['show_timers'])
        def show_timers(message):
            user_timers = self.cactus.get_user_timers()

            if len(user_timers) > 0:
                timers_message = "Here are your reminders:\n"
                for timer in user_timers:
                    timer_date = timer["date_time"].strftime("%d/%m/%Y %H:%M")
                    timers_message += f"\n- {timer_date}"
            else:
                timers_message = "You have no reminders"
            self.bot.send_message(message.chat.id, timers_message)

        @self.bot.message_handler(commands=['delete_reminder'])
        def delete_reminder(message):
            user_reminders = self.cactus.get_user_reminders()
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

        @self.bot.message_handler(commands=['plot_temperature'])
        def show_temperature(message):
            user_choice = "Which data are you interested in?"
            options = [("today", "1"),
                       ("last 7 days", "7"),
                       ("last 15 days", "15"),
                       ("last 30 days", "30")]

            markup = InlineKeyboardMarkup()
            markup.row_width = 1
            markup.add(
                *[InlineKeyboardButton(
                    option, callback_data="plot_temperature_" + option_id
                ) for option, option_id in options]
            )

            self._awaiting_temperature_plot = True
            self.bot.send_message(chat_id=message.chat.id, text=user_choice, reply_markup=markup)

        @self.bot.message_handler(commands=['plot_humidity'])
        def show_temperature(message):
            user_choice = "Which data are you interested in?"
            options = [("today's", "1"),
                       ("last 7 days", "7"),
                       ("last 15 days", "15"),
                       ("last 30 days", "30")]

            markup = InlineKeyboardMarkup()
            markup.row_width = 1
            markup.add(
                *[InlineKeyboardButton(
                    option, callback_data="plot_humidity_" + option_id
                ) for option, option_id in options]
            )

            self._awaiting_humidity_plot = True
            self.bot.send_message(chat_id=message.chat.id, text=user_choice, reply_markup=markup)

        @self.bot.message_handler(commands=['delete_timer'])
        def delete_timer(message):
            user_timers = self.cactus.get_user_timers()
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

        @self.bot.message_handler(commands=['show_voice_preference'])
        def show_voice_preference(message):
            voice_preference = self.cactus.get_user_voice_preference()
            user_answer = f"Your voice preference is: '{voice_preference}'"
            self.bot.send_message(message.chat.id, user_answer)

        @self.bot.message_handler(commands=['show_username'])
        def show_username(message):
            username = self.cactus.get_user_name()
            user_answer = f"Your username is: '{username}'"
            self.bot.send_message(message.chat.id, user_answer)

        @self.bot.message_handler(commands=['show_init'])
        def set_llm_initialization_prompt(message):
            init_prompt = self.cactus.get_user_initialization_prompt()

            if init_prompt != "":
                pre = "Your current initialization prompt is:\n\n"
                post = "\n\nIs there something else I can do for you?"

                self.bot.send_message(message.chat.id, pre + init_prompt + post)

            else:
                self.bot.send_message(message.chat.id,
                                  f"You did not set an initialization prompt. You can do so with the command \\init_prompt")

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            chat_id = call.message.chat.id
            message_id = call.message.message_id

            # Remove buttons by editing the message and setting reply_markup=None
            self.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)

            if call.data.startswith("delete_reminder_"):
                reminder_id = call.data.replace("delete_reminder_", "", 1)
                self.cactus.remove_reminder(reminder_id=reminder_id)
                self.bot.send_message(chat_id, f"Reminder deleted. 🗑️")

            elif call.data.startswith("delete_timer_"):
                timer_id = call.data.replace("delete_timer_", "", 1)
                self.cactus.remove_timer(timer_id=timer_id)
                self.bot.send_message(chat_id, f"Timer deleted. 🗑️")

            elif call.data.startswith("set_voice_preference_"):
                language_voice = call.data.replace("set_voice_preference_", "", 1)
                language, voice = language_voice.split("-")
                self.cactus.set_user_language_preference(language_preference=language)
                self.cactus.set_user_voice_preference(voice_preference=voice)
                self.bot.send_message(chat_id, f"Voice preference set! 🗣️️")

            elif call.data.startswith("plot_humidity_"):
                time = call.data.replace("plot_humidity_", "", 1)
                days = int(time)
                self.send_plot_to_telegram(chat_id=chat_id, days=days, data="humidity")
                self._awaiting_humidity_plot = False

            elif call.data.startswith("plot_temperature_"):
                time = call.data.replace("plot_temperature_", "", 1)
                days = int(time)
                self.send_plot_to_telegram(chat_id=chat_id, days=days, data="temperature")
                self._awaiting_temperature_plot = False

        @self.bot.message_handler(func=lambda msg: True)
        def handle_message(message):
            self.handle_user_request(message, BOT_SENDER_ID)

    ###############################################################################################
    #
    # Cactus/ESP32 methods
    #
    ###############################################################################################
    async def get_sensor_data(self):
        while True:
            await asyncio.sleep(SECONDS_DELAY_SENSOR_DATA)
            temperature, humidity = self.get_current_temperature_humidity()

            if temperature and humidity:
                try:
                    point = (
                        Point("sensor")
                        .field("temperature", temperature)
                        .field("humidity", humidity)
                    )
                    self.influxdb_client.write(database="cactus_sensor_data", record=point)

                except Exception as e:
                    print(f"ERROR: Failed to send data to influxdb. {e}")

    async def monitor_mic_registration(self):
        while True:
            try:
                esp32_ip = os.getenv('ESP32_IP', '')

                response = requests.get(f"http://{esp32_ip}/microphone", timeout=5)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")
                if "audio/wav" in content_type:
                    text = self.cactus.speech_to_text(response.content)
                    self.handle_user_request(text, CACTUS_SENDER_ID)

            except requests.exceptions.Timeout:
                print("ERROR: Response timeout while fetching sensor data.")
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch sensor data: {e}")

            await asyncio.sleep(SECONDS_DELAY_SENSOR_DATA)

    def get_influxdb_data(self, days, data):
        query = f"SELECT time, {data} FROM 'sensor' WHERE time >= now() - interval '{days} days'"
        df = self.influxdb_client.query(query=query, database="cactus_sensor_data", language='sql', mode="pandas")
        return df

    def send_plot_to_telegram(self, chat_id, days, data):
        df_to_plot = self.get_influxdb_data(days=days, data=data)

        # Convert 'time' to datetime
        df_to_plot["time"] = pd.to_datetime(df_to_plot["time"])

        plt.figure(figsize=(10, 6))
        label = "Temperature" if data == "temperature" else "Humidity"
        unit = " (°C)" if data == "temperature" else " (%)"
        plt.plot(df_to_plot["time"], df_to_plot[data], marker='o', linestyle='-', label=label + unit)

        # Formatting
        plt.xlabel("Time")
        plt.ylabel(label)
        plt.title(f"{label} Over {days} day(s)")
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid()

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        # Send the image to Telegram
        self.bot.send_photo(chat_id, photo=buf)

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

    def get_current_temperature_humidity(self):
        temperature = None
        humidity = None

        try:
            esp32_ip = os.getenv('ESP32_IP', '')

            response = requests.get(f"http://{esp32_ip}/sensor", timeout=5)
            response.raise_for_status()

            temperature = response.text["temperature"]
            humidity = response.text["humidity"]
        except requests.exceptions.Timeout:
            print("ERROR: Response timeout while fetching sensor data.")
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch sensor data: {e}")

        return temperature, humidity

    def set_reminder(self, request, chat_id, sender):
        llm_response = self.cactus.get_gemini_response(request=get_reminder_check_prompt(request),
                                                       initialization_prompt="")
        action_dict = json.loads(extract_between_braces(llm_response))
        reminder_date_time, user_message = extract_exact_datetime(action_dict)
        if user_message and not reminder_date_time:
            if sender == BOT_SENDER_ID:
                self.bot.send_message(chat_id, user_message)
            else:
                self.cactus_speak(user_message)

        reminder_title = action_dict["content"]

        if reminder_date_time:
            reminder_id = len(self.cactus.get_user_reminders()) + 1
            new_reminder = {
                "reminder": reminder_title,
                "date_time": reminder_date_time,
                "reminder_id": reminder_id
            }
            self.cactus.set_reminder(reminder=new_reminder)

            # Send confirmation message
            confirmation_message = f"Reminder set: {reminder_title}. " + format_datetime_natural(reminder_date_time)

            if sender == BOT_SENDER_ID:
                self.bot.send_message(chat_id, confirmation_message + " ✅")
            else:
                self.cactus_speak(confirmation_message)
        else:
            repeat_message = "Sorry, I did not understand, can you rephrase the request clarifying the date and/or time?"
            if sender == BOT_SENDER_ID:
                self.bot.send_message(chat_id, repeat_message)
            else:
                self.cactus_speak(repeat_message)

    def set_timer(self, request, chat_id, sender):
        llm_response = self.cactus.get_gemini_response(request=get_timer_set_prompt(request),
                                                       initialization_prompt="")

        action_dict = json.loads(extract_between_braces(llm_response))
        timer_date_time, user_message = extract_exact_datetime(action_dict)
        if user_message and not timer_date_time:
            if sender == BOT_SENDER_ID:
                self.bot.send_message(chat_id, user_message)
            else:
                self.cactus_speak(user_message)

        if timer_date_time:
            timer_id = len(self.cactus.get_user_timers())+1
            new_timer = {"date_time": timer_date_time, "timer_id": timer_id}
            self.cactus.set_timer(timer=new_timer)

            # Send confirmation message
            if sender == BOT_SENDER_ID:
                self.bot.send_message(chat_id, f"{parse_time_delay(action_dict['time_value'])} timer confirmed! ✅")
            else:
                self.cactus_speak(f"{parse_time_delay(action_dict['time_value'])} timer confirmed!")
        else:
            repeat_message = "Sorry, I did not understand, can you rephrase the request clarifying the time?"
            if sender == BOT_SENDER_ID:
                self.bot.send_message(chat_id, repeat_message)
            else:
                self.cactus_speak(repeat_message)

    async def check_timers_and_reminders(self):
        while True:
            now = datetime.now()
            reminders = self.cactus.get_user_reminders()
            timers = self.cactus.get_user_timers()
            chat_id = self.cactus.get_user_chat_id()
            username = self.cactus.get_user_name()

            if reminders:
                for reminder in reminders:
                    reminder_time = reminder["date_time"]

                    if reminder_time and isinstance(reminder_time, str):
                        reminder_time = datetime.fromisoformat(reminder_time)
                    if reminder_time <= now:
                        try:
                            if chat_id:
                                self.bot.send_message(reminder["chat_id"], f"⏰ Reminder: {reminder['reminder']}")
                        except ApiTelegramException:
                            print(f"Bad Request: chat {reminder['chat_id']} not found")

                        cactus_alert = f"Hey {username}, I'm here to remind you: {reminder['reminder']}"
                        self.cactus_speak(cactus_alert)
                        self.cactus.remove_reminder(reminder_id=reminder["reminder_id"])

            if timers:
                for timer in timers:
                    timer_time = timer["date_time"]

                    if timer_time and isinstance(timer_time, str):
                        timer_time = datetime.fromisoformat(timer_time)
                    if timer_time <= now:
                        try:
                            if chat_id:
                                self.bot.send_message(timer["chat_id"], f"⏰ Time's up! ⏰")
                        except ApiTelegramException:
                            print(f"Bad Request: chat {timer['chat_id']} not found")

                        cactus_alert = f"Hey {username}, time's up!"
                        self.cactus_speak(cactus_alert)
                        self.cactus.remove_timer(timer_id=timer["timer_id"])

            await asyncio.sleep(1)

    def cactus_speak(self, response):
        user_language_preference = self.cactus.get_user_language_preference()
        user_voice_preference = self.cactus.get_user_voice_preference()

        payload = {"phrasetospeak": response}

        try:
            esp32_ip = os.getenv('ESP32_IP', '')

            response = requests.post(f"http://{esp32_ip}/message_speak", data=payload, timeout=5)
            response.raise_for_status()

            try:
                response_data = response.json()
                print(f"Response payload: {response_data}")
                return response_data
            except requests.exceptions.JSONDecodeError:
                print(f"Response is not in JSON format: {response.text}")
                return response.text

        except requests.exceptions.Timeout:
            print("ERROR: Response timeout. The ESP32 didn't reply.")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send request: {e}")

    def handle_user_request(self, message, sender):
        if sender == BOT_SENDER_ID:
            chat_id = message.chat.id
            message = message.text
            self.cactus.set_chat_id(chat_id)
        else:
            chat_id = self.cactus.get_user_chat_id()

        # user just entered the new initialization prompt
        if self._awaiting_init_prompt:
            self.cactus.set_user_initialization_prompt(initialization_prompt=message)
            self._awaiting_init_prompt = False

            if sender == BOT_SENDER_ID:
                self.bot.send_message(chat_id, INITIALIZATION_PROMPT_CONFIRMATION)

        # user just entered the new username
        elif self._awaiting_user_name:
            self.cactus.set_user_name(username=message)
            self._awaiting_user_name = False

            if sender == BOT_SENDER_ID:
                self.bot.send_message(chat_id, f"Thanks {message}! " + USERNAME_CONFIRMATION)

        # user is sending a new message
        else:
            # check if an action is required
            action_id = self.action_is_required(request=message)

            # user asked to set reminder
            if REMINDER_ACTION_ID in action_id:
                self.set_reminder(message, chat_id, sender)

            # user asked to set timer
            elif TIMER_ACTION_ID in action_id:
                self.set_timer(message, chat_id, sender)

            else:
                username = self.cactus.get_user_name()
                user_init_prompt = self.cactus.get_user_initialization_prompt()
                temperature, humidity = self.get_current_temperature_humidity()
                intro_to_user_message = "\n\n## USER MESSAGE:\n"

                # user asked for information about its data
                if SYSTEM_INFO_ID in action_id:
                    system_initialization_prompt = get_cactus_base_instructions_short(sender=sender,
                                                                                      user_name=username,
                                                                                      temperature=temperature,
                                                                                      humidity=humidity,
                                                                                      user_initialization_prompt=user_init_prompt)
                    user_info = self.cactus.get_string_user_info()
                    init_prompt = system_initialization_prompt + user_info + intro_to_user_message
                    llm_response = self.cactus.get_gemini_response(request=message,
                                                                   initialization_prompt=init_prompt)

                    if sender == BOT_SENDER_ID:
                        self.bot.send_message(chat_id, llm_response)
                    else:
                        self.cactus_speak(llm_response)

                # no action required
                elif NO_ACTION_REQUIRED_ID in action_id:
                    system_initialization_prompt = get_cactus_base_instructions(sender=sender,
                                                                                user_name=username,
                                                                                temperature=temperature,
                                                                                humidity=humidity,
                                                                                user_initialization_prompt=user_init_prompt)

                    init_prompt = system_initialization_prompt + intro_to_user_message
                    llm_response = self.cactus.get_gemini_response(request=message,
                                                                   initialization_prompt=init_prompt)

                    if sender == BOT_SENDER_ID:
                        self.bot.send_message(chat_id, llm_response)
                    else:
                        self.cactus_speak(llm_response)
