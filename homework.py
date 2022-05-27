import logging
import os
from time import time, sleep

import requests
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Bot
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат"""
    bot().send_message(
        chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервиса. В качестве параметра функция
    получает временную метку. В случае успешного запроса  ответ API,
    преобразовав его из формата JSON к типам данных Python."""
    timestamp = current_timestamp or int(time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность. Если ответ API соответствует
    ожиданиям, то функция возвращает список домашних работ"""
    if type(response) == dict:
        return response.get('homeworks')


def parse_status(homework):
    """извлекает из информации о конкретной
    домашней работе статус этой работы."""
    homework_name = homework.get('lesson_name')
    homework_status = homework.get('status')
    #...
    verdict = HOMEWORK_STATUSES[homework_status]
    #...
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения"""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and PRACTICUM_TOKEN:
        return True
    return False


def main():
    """Основная логика работы бота."""

    #...

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time())

    #...

    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_response(response)
            #...

            current_timestamp = ...
            sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            #...
            sleep(RETRY_TIME)
        else:
            #...


if __name__ == '__main__':
    #main()
    print(check_tokens())
    print(get_api_answer(1))
