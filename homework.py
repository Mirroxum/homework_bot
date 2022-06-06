import logging
import os
import sys
from http import HTTPStatus
from time import sleep, time

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

from exception_bot import (KeyMissError, JSONError,
                           RequestError, HTTPStatusNotOK)

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
TIMEOUT_SERVER = 5
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
    except TelegramError as e:
        raise TelegramError(
            f'Cбой при отправке сообщения "{message}" в Telegram.') from e
    else:
        logger.info('Удачная отправка сообщения')


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса ответ API, преобразовав его
    из формата JSON к типам данных Python.
    """
    request_value = [ENDPOINT, HEADERS, {'from_date': current_timestamp}]
    try:
        endpoint, headers, params = request_value
        response = requests.get(endpoint,
                                headers=headers,
                                params=params,
                                timeout=TIMEOUT_SERVER)
        if response.status_code != HTTPStatus.OK:
            raise HTTPStatusNotOK(
                f'API вернул код отличный от 200: {response.status_code}!')
        logger.info('Ответ от сервера получен')
        return response.json()
    except TimeoutError as e:
        raise TimeoutError('Превышено время ожидания от сервера') from e
    except ConnectionError as e:
        raise ConnectionError(
            'Произошла ошибка при попытке запроса ',
            f'к API c параметрами: {request_value}') from e
    except requests.exceptions.JSONDecodeError as e:
        raise JSONError(
            f'Сбой декодирования JSON из ответа: {response} ',
            f'с параметрами: {request_value}') from e
    except requests.exceptions.RequestException as e:
        raise RequestError(
            'Ошибка вызванная request. При попытке сделать',
            f'запрос с параметрами {request_value}') from e


def check_response(response):
    """Проверяет ответ API на корректность.
    Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Получен некорректный тип response')
    if 'homeworks' not in response.keys():
        raise KeyMissError(
            f'В ответе отсвутствует ключ homeworks.Response:{response}')
    if 'current_date' not in response.keys():
        raise KeyMissError(
            f'В ответе отсвутствует ключ current_date.Response:{response}')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Получен некорректный тип homeworks')
    logger.info('Получен корректный ответ от API')
    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации статус работы."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICT.get(homework_status)
    if homework_status is None:
        raise KeyError(
            f'В homework отсутствует нужноее поле status.Homework: {homework}')
    if homework_name is None:
        raise KeyError(
            f'В homework отсутствует нужноее поле name.Homework: {homework}')
    if verdict is None:
        raise KeyError(
            f'Неизвестный статус работы. status: {homework_status}')
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
            if len(check_response(response)):
                send_message(bot, parse_status(check_response(response).pop()))
                current_timestamp = response['current_date']
            else:
                logger.info('Обновлений нет')
        except Exception as error:
            message = ('Сбой в работе программы.')
            logger.error(message, exc_info=True)
            if message != error_cache_message and type(error) != KeyMissError:
                send_message(bot, message)
                error_cache_message = message
        finally:
            sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
