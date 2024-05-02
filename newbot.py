import telebot
import os
from dotenv import load_dotenv
import logging
from db import *
from buttons import create_key
from Speechkit import speech_to_text, text_to_speech, is_stt_block_limit, stt_symbols_db_to_text, tokens_control, \
    stt_symbols_db
from Tokenizer import *
from GPT import *

load_dotenv()

logging.basicConfig(filename=os.getenv('file_error'), level=logging.ERROR, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(os.getenv("TOKEN"))


@bot.message_handler(commands=['debug'], func=lambda message: message.from_user.id == 5085094693)
def debug(message):
    with open('errors.cod.log', 'rb') as er:
        bot.send_document(message.chat.id, er)


@bot.message_handler(commands=["start"])
def start_handler(message):
    db_user = CreateDatabase()
    if not db_user.check_user_exists(message.chat.id):
        db_user.add_user(message.chat.id)
        bot.send_message(message.chat.id, "Привет, Я Бот голосовой помощник", reply_markup=create_key())
    else:
        bot.send_message(message.chat.id, "Привет, Я Бот голосовой помощник", reply_markup=create_key())


# commadns, ya sam chet xz tak li ix nado delat


@bot.message_handler(commands=["tts"])
def send_tts(message):
    bot.send_message(message.chat.id, 'Введи текстовое сообщение:')

    def text_user1(message):
        text_message = message.text

        if message.content_type != 'text':
            bot.send_message(message.chat.id, 'Отправь текстовое сообщение')

            bot.register_next_step_handler(message, text_user1)

            return

        if len(text_message) > 50:
            bot.send_message(message.chat.id, 'Сообщение слишком большое')

            bot.register_next_step_handler(message, text_user1)

            return

        user_id = message.chat.id
        info_db_tokens = tokens_user()
        tokens_db = info_db_tokens.tts_symbols_user(user_id)
        info_db_tokens.close()
        if tokens_db != None and tokens_db > 0:
            save_text = message_add()
            save_text.add_text(text_message, user_id)
            save_text.close()
            info_tokens = tokens_control(text_message)
            info_db_tokens1 = tokens_user()
            tokens_db1 = info_db_tokens1.tts_symbols_user(user_id)
            result = tokens_db1 - info_tokens
            info_db_tokens1.close()
            save_tokens = tokens_add()
            save_tokens.add_tts_symbols(result, user_id)
            save_tokens.close()
            success, response = text_to_speech(text_message)
            bot.send_message(message.chat.id, "Ожидайте ответа")
            if success:
                bot.send_voice(message.chat.id, response)
            else:
                bot.send_message(message.chat.id, "Ошибка:", response)
        else:
            bot.send_message(message.chat.id, 'Символы закончились!')

    bot.register_next_step_handler(message, text_user1)


@bot.message_handler(commands=["stt"])
def voice_input(message):
    bot.send_message(message.chat.id, "Запиши голосовое, которое нужно распознать")
    bot.register_next_step_handler(message, voice_gpt)


def voice_gpt(message):
    user_id = message.chat.id
    if not message.voice:
        return

    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)

    duration_user = message.voice.duration
    user_id = message.chat.id
    result_info = is_stt_block_limit(user_id=user_id, duration=duration_user)
    if result_info == 'Превышено длительность голосового сообщения' or result_info == 'Превышен лимит для пользователя':
        bot.send_message(message.chat.id, result_info)
        return

    voice_speechkit = speech_to_text(file)
    stt_symbols_db(user_id, voice_speechkit)
    bot.send_message(message.chat.id, f'<i>*{voice_speechkit}.*</i>', parse_mode='html')


# handlers_user


@bot.message_handler(content_types=["voice"])
def voice_message_handler_message(message):
    voice = message.voice.file_id
    user_id = message.chat.id
    info_tokens = TotalGptTokensInfo()
    result_tokens = info_tokens.total_gpt_tokens_user(user_id)
    info_tts = TtsSymbolsInfo()
    result_tts = info_tts.tts_symbols_user(user_id)
    info_tts.close()
    info_tokens.close()
    if result_tokens is None or result_tokens < 0:
        result_tokens = 0
    if result_tts is None or result_tts < 0:
        result_tts = 0
    if int(result_tokens) > 0 and int(result_tts) > 0:
        file_info = bot.get_file(voice)
        file = bot.download_file(file_info.file_path)
        duration_user = message.voice.duration
        result_info = is_stt_block_limit(user_id=user_id, duration=duration_user)
        if result_info == 'Превышено длительность голосового сообщения' or result_info == 'Превышен лимит для пользователя':
            bot.send_message(message.chat.id, result_info, reply_markup=create_key())
            return
        voice_speechkit = speech_to_text(file)
        if voice_speechkit != 'При запросе возникла ошибка':
            gpt_response = promt_gpt(voice_speechkit)
            if gpt_response != 'Ошибка':
                tokenizer = count_tokens(voice_speechkit + gpt_response)
                save_tokens = TotalGptTokensAdd()
                save_tokens.add_total_gpt_tokens(result_tokens - tokenizer, user_id)
                save_tokens.close()
                status, result_text = text_to_speech(gpt_response)
                if result_text != 'При запросе возникла ошибка':
                    stt_symbols_db_to_text(user_id, voice_speechkit)
                    stt_symbols_db_to_text(user_id, gpt_response)
                    bot.send_voice(message.chat.id, result_text, reply_markup=create_key())
                else:
                    bot.send_message(message.chat.id, "При запросе возникла ошибка", reply_markup=create_key())
            else:
                bot.send_message(message.chat.id, "При запросе в нейросеть произошла ошибка",
                                 reply_markup=create_key())
        else:
            bot.send_message(message.chat.id, "При запросе произошла ошибка", reply_markup=create_key())

    else:
        bot.send_message(message.chat.id, "Запросы закончились!", reply_markup=create_key())


@bot.message_handler(content_types=["text"])
def text_message_handler_message(message):
    text = message.text
    user_id = message.chat.id
    info_tokens = TotalGptTokensInfo()
    result_tokens = info_tokens.total_gpt_tokens_user(user_id)
    info_tokens.close()
    if result_tokens is None or result_tokens < 0:
        result_tokens = 0
    if int(result_tokens) > 0:
        gpt_response = promt_gpt(text)
        if gpt_response != 'Ошибка':
            bot.send_message(message.chat.id, gpt_response, reply_markup=create_key())
            stt_symbols_db_to_text(user_id, text)
            stt_symbols_db_to_text(user_id, gpt_response)
            tokenizer = count_tokens(text + gpt_response)
            save_tokens = TotalGptTokensAdd()
            save_tokens.add_total_gpt_tokens(result_tokens - tokenizer, user_id)
            save_tokens.close()
        else:
            bot.send_message(message.chat.id, 'Произошла ошибка в \n'
                                              'нейросети!', reply_markup=create_key())
    else:
        bot.send_message(message.chat.id, 'Запросы закончились!', reply_markup=create_key())


bot.polling()
