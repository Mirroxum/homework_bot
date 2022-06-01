import logging
import os
import sys
import traceback
from http import HTTPStatus
from time import sleep, time

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(lineno)d.%(levelname)s(%(funcName)s) - %(message)s'))
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICT = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Удачная отправка сообщения')
    except TelegramError:
        logger.error(
            f'Cбой при отправке сообщения "{message}" в Telegram.', exc_info=True)


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса ответ API, преобразовав его
    из формата JSON к типам данных Python.
    """
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params={'from_date': current_timestamp})
    except Exception:
        logger.error(
        f'Сбой при попытке запросв к API: {response}', exc_info=True)
    if response.status_code != HTTPStatus.OK:
        raise ConnectionError(
            f'API вернул код отличный от 200: {response.status_code}!')
    logger.info('Ответ от сервера получен')
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        logger.error(
        f'Сбой декодирования JSON из ответа: {response}', exc_info=True)


def check_response(response):
    """Проверяет ответ API на корректность.
    Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Получен некорректный тип response')
    if not 'current_date' or 'homeworks' not in response.keys():
        raise ValueError('В ответе отсвутствуют нужные ключи')
    if not response:
        raise ValueError('Пустой список')
    homeworks_response = response['homeworks']
    if not isinstance(homeworks_response, list):
        raise TypeError('Получен некорректный тип homeworks')
    logger.info('Получен корректный ответ от API')
    return homeworks_response


def parse_status(homework):
    """Извлекает из информации статус работы."""
    if not len(homework):
        return None
    if 'homework_name' and 'status' not in homework.keys():
        raise TypeError(f'В homework отсутствуют необходимые поля: {homework}')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if verdict := HOMEWORK_VERDICT.get(homework_status):
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise KeyError('Недокументированный статус домашней работы,',
            f'обнаруженный в ответе: {homework_status}')


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and PRACTICUM_TOKEN:
        return True
    logger.critical('Отсутствуют обязательные переменные окружения')
    return False


def main():
    """Основная логика работы бота."""
    if check_tokens():
        error_cache_message = ''
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time())
        logger.info('Инициализация прошла успешно')
    else:
        sys.exit('Отсутствуют обязательные переменные окружения')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if homework := check_response(response):
                send_message(bot, parse_status(homework.pop()))
                current_timestamp = response['current_date']
            else:
                logger.info('Обновлений нет')
            sleep(RETRY_TIME)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback_print = ''.join(traceback.format_tb(exc_traceback))
            message = f'Сбой в работе программы.\nТип: {exc_type.__name__}.\nОписание:{exc_value}.\nМесто ошибки:{traceback_print}'
            logger.error(message)
            if message != error_cache_message:
                send_message(bot, message)
                error_cache_message = message
            sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
