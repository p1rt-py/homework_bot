import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (StatusCodeError)

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

TOKEN_ERROR = 'Oшибка переменных окружения'


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception as error:
        raise SystemError('Ошибка отправки сообщения в Telegramm') from error


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': current_timestamp}
    try:
        hw_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if hw_status.status_code != HTTPStatus.OK:
            raise StatusCodeError(f'Ошибка {hw_status.status_code}')
        return hw_status.json()
    except Exception as error:
        raise SystemError(f'Ошибка при запросе: {error}')


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info('Проверка ответа от API')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Отсутствует ключ')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Ответ API не является листом')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о  домашней работе."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Функция main в ней описана основная логика работы программы."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    ERROR_CACHE_MESSAGE = ''
    if not check_tokens():
        logger.critical(TOKEN_ERROR)
        sys.exit(TOKEN_ERROR)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            hw_list = check_response(response)
            if hw_list:
                send_message(bot, parse_status(hw_list[0]))
            else:
                logger.debug('Нет новых статусов')
                raise Exception('Нет новых статусов')
        except Exception as error:
            logger.error(error)
            message_error = str(error)
            if message_error != ERROR_CACHE_MESSAGE:
                send_message(bot, message_error)
                ERROR_CACHE_MESSAGE = message_error
        finally:
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='homework.log',
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    main()
