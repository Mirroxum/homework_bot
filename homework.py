import logging
import os
import sys
from time import time, sleep
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(levelname)s  - %(message)s',
    level=logging.INFO,
    stream=sys.stdout)

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
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info('Удачная отправка сообщения')
    except Exception as error:
        logging.error(f'Cбой при отправке сообщения в Telegram: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса ответ API, преобразовав его
    из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        logging.error(
            f'API вернул код отличный от 200: {response.status_code}!')
        raise ConnectionError


def check_response(response):
    """Проверяет ответ API на корректность.
    Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    if isinstance(response, dict):
        if 'curent_date' and 'homeworks' in response.keys():
            if response:
                homeworks_response = response['homeworks']
                logging.info('Получен корректный ответ от API')
                if isinstance(homeworks_response, list):
                    return homeworks_response
                else:
                    logging.error('Получен некорректный тип homeworks')
                    raise TypeError
            else:
                logging.error('Пустой список')
                raise ValueError
        else:
            logging.error('В ответе отсвутствуют нужные ключи')
            raise ValueError
    else:
        logging.error('Получен некорректный тип response')
        raise TypeError


def parse_status(homework):
    """Извлекает из информации статус работы."""
    if len(homework):
        homework_name = homework['homework_name']
        homework_status = homework['status']
        try:
            verdict = HOMEWORK_STATUSES[homework_status]
        except KeyError as error:
            logging.error(
                'Недокументированный статус домашней работы,',
                f'обнаруженный в ответе: {error}')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        return None


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and PRACTICUM_TOKEN:
        return True
    logging.critical('Отсутствуют обязательные переменные окружения')
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
                current_timestamp = response['current_date']
            else:
                logging.info('Обновлений нет')
            sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)
            sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
