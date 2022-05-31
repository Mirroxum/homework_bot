import json
import logging
import os
import sys
from time import time, sleep
from http import HTTPStatus
from turtle import home

import requests
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Bot
from telegram.ext import Updater, MessageHandler

from my_except import ServerError

load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(levelname)s  - %(message)s',
    level=logging.INFO,
    stream=sys.stdout)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат"""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info('Удачная отправка сообщения')
    except Exception as error:
        logging.error(f'Cбой при отправке сообщения в Telegram: {error}')



def get_api_answer(current_timestamp):
    """Делает запрос к API-сервиса. В качестве параметра функция
    получает временную метку. В случае успешного запроса  ответ API,
    преобразовав его из формата JSON к типам данных Python."""
    timestamp = current_timestamp or int(time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        return response.json()
    except ConnectionError as error:
        logging.error(f'Сбой при запросе к эндпоинту: {error}')


def check_response(response):
    """Проверяет ответ API на корректность. Если ответ API соответствует
    ожиданиям, то функция возвращает список домашних работ"""
    try:
        if response != HTTPStatus.OK:
            raise ServerError
        elif len(response.json()):
            raise ValueError
        response.get('current_date')
        homeworks_response = response.get('homeworks')
        logging.info('Корректный ответ от API')
        return homeworks_response
    except ValueError as error:
        logging.error(f'Некорректный ответ от API: {error}')
    except ServerError as error:
        logging.error('Ошибка сервера')


def parse_status(homework):
    """извлекает из информации о конкретной
    домашней работе статус этой работы."""
    if len(homework):
        homework_name = homework.get('lesson_name')
        homework_status = homework.get('status')
        try:
            verdict = HOMEWORK_STATUSES[homework_status]
        except KeyError as error:
            logging.error(f'Недокументированный статус домашней работы, обнаруженный в ответе: {error}')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        return None
    


def check_tokens():
    """Проверяет доступность переменных окружения"""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and PRACTICUM_TOKEN:
        return True
    logging.critical(f'Отсутствие обязательных переменных окружения во время запуска бота')
    return False


def main():
    """Основная логика работы бота."""
    if check_tokens: 
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time())
    logging.info('Инициализация прошла успешно')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework.pop()))
                current_timestamp = response.get('current_date')
            else:
                logging.info('Обновлений нет')
            sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)
            sleep(RETRY_TIME)
        else:
            break
            


if __name__ == '__main__':
    main()
