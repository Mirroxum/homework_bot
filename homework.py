import logging
import os
import sys
from http import HTTPStatus
from time import sleep, time

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

from exception_bot import KeyMissingError

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(lineno)d.%(levelname)s(%(funcName)s) - %(message)s'))
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
            f'Cбой при отправке сообщения "{message}" в Telegram.',
            exc_info=True)


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса ответ API, преобразовав его
    из формата JSON к типам данных Python.
    """
    request_value = {'endpoint': ENDPOINT,
                     'headers': HEADERS,
                     'params': {'from_date': current_timestamp}}
    try:
        response = requests.get(request_value['endpoint'],
                                headers=request_value['headers'],
                                params=request_value['params'])
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError(
                f'API вернул код отличный от 200: {response.status_code}!')
        logger.info('Ответ от сервера получен')
        return response.json()
    except ConnectionError as e:
        raise ConnectionError(
            'Произошла ошибка при попытке запроса ',
            f'к API c параметрами: {request_value}') from e
    except ValueError as e:
        raise ValueError(
            f'Сбой декодирования JSON из ответа: {response} ',
            f'с параметрами: {request_value}') from e


def check_response(response):
    """Проверяет ответ API на корректность.
    Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    if not response:
        raise ValueError('Пустой список')
    if not isinstance(response, dict):
        raise TypeError('Получен некорректный тип response')
    if 'homeworks' not in response.keys():
        raise KeyMissingError('В ответе отсвутствует нужный ключ homeworks')
    if 'current_date' not in response.keys():
        raise KeyMissingError('В ответе отсвутствует нужный ключ current_date')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Получен некорректный тип homeworks')
    logger.info('Получен корректный ответ от API')
    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации статус работы."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework.keys():
        raise TypeError(
            f'В homework отсутствует поле homework_name: {homework}')
    if 'status' not in homework.keys():
        raise TypeError(
            f'В homework отсутствует поле status: {homework}')
    verdict = HOMEWORK_VERDICT[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and PRACTICUM_TOKEN


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения')
        sys.exit('Отсутствуют обязательные переменные окружения')
    error_cache_message = ''
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time())
    logger.info('Инициализация прошла успешно')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if check_response(response) == {}:
                send_message(bot, parse_status(check_response(response).pop()))
                current_timestamp = response['current_date']
            else:
                logger.info('Обновлений нет')
            sleep(RETRY_TIME)
        except Exception as error:
            message = ('Сбой в работе программы.')
            logger.error(message, exc_info=True)
            if message != error_cache_message and error != KeyMissingError:
                send_message(bot, message)
                error_cache_message = message
            sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
