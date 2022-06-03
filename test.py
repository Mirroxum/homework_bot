import logging
import sys

from requests import request

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(lineno)d.%(levelname)s(%(funcName)s) - %(message)s'))
logger.addHandler(handler)

def test():
    try:
        return 5/0
    except ZeroDivisionError as e:
        raise requests.exceptions.JSONDecodeError('Первая ошибка') from e


def test_two():
    raise ValueError('Вторая ошибка')

def main():
    try:
        test_dict = {
            'value1': 1,
            'value2': 2
        }
        if (('value3' and 'value1') in test_dict.keys()):
            print(True)
        else: print(False)
    except Exception as error:
        logger.error(f'ошибка {error}')



if __name__ == '__main__':
    main()