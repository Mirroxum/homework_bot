import logging
import os
import sys
from http import HTTPStatus
from time import sleep, time
from typing import final

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

from exception_bot import (KeyMissError, JSONError, TGError,
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

RETRY_TIME = 5
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
        raise TGError(
            f'Cбой при отправке сообщения "{message}" в Telegram.') from e
    else:
        logger.info('Удачная отправка сообщения')


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса ответ API, преобразовав его
    из формата JSON к типам данных Python.
    """
    request_value = [ENDPOINT, HEADERS,
                     {'from_date': current_timestamp}, TIMEOUT_SERVER]
    try:
        endpoint, headers, params, timeout = request_value
        response = requests.get(endpoint,
                                headers=headers,
                                params=params,
                                timeout=timeout)
        if response.status_code != HTTPStatus.OK:
            raise HTTPStatusNotOK()
        homework = response.json()
    except HTTPStatusNotOK as e:
        raise HTTPStatusNotOK(
                'API вернул код отличный от 200',
                f'Статус: {response.status_code}!') from e
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
    else:
        logger.info('Ответ от сервера получен')
        return homework


def check_response(response):
    """Проверяет ответ API на корректность.
    Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    try:
        if not isinstance(response, dict):
            raise TypeError()
        if 'homeworks' not in response.keys():
            raise KeyMissError()
        if 'current_date' not in response.keys():
            raise KeyMissError()
        if not isinstance(response['homeworks'], list):
            raise TypeError()
    except KeyMissError as e:
        raise KeyMissError(
                'В ответе отсвутствует ключ необходимый ключ.',
                f'Response:{response}') from e
    except TypeError as e:
        raise TypeError('Получен некорректный тип переменных') from e
    else:
        logger.info('Получен корректный ответ от API')
        return response['homeworks']

 
        


def parse_status(homework):
    """Извлекает из информации статус работы."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICT.get(homework_status)
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
        except KeyMissError:
            logger.error('Сбой в работе программы.', exc_info=True)
        except Exception:
            message = ('Сбой в работе программы.')
            logger.error(message, exc_info=True)
            send_message(bot, message)
        finally:
            sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
