import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (StatusCodeError, TokenError)

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
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception as error:
        raise SystemError('Ошибка отправки сообщения в Telegramm') from error


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        hw_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise SystemError(f'Ошибка при запросе: {error}')
    if hw_status.status_code != HTTPStatus.OK:
        status_code = hw_status.status_code
        raise StatusCodeError(f'Ошибка {status_code}')
    try:
        return hw_status.json()
    except ValueError:
        raise ValueError('Ошибка парсинга')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) == dict:
        response['current_date']
        homeworks = response['homeworks']
        if type(homeworks) == list:
            return homeworks
        else:
            raise KeyError('Отсутствует ключа homeworks')
    else:
        raise TypeError('Ответ API не является словарем')


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
    STATUS = ''
    ERROR_CACHE_MESSAGE = ''
    if not check_tokens():
        logger.critical('Ошибка переменных окружения')
        raise TokenError('Ошибка переменных окружения')
        # я оставлю пока рейз, хоть ты и сказал, что надо sys.exit, но при
        # этом для количества мне надо исключений добавить)
        sys.exit('Выйдите из интерпретатора, подняв SystemExit')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response))
            if message != STATUS:
                send_message(bot, message)
                STATUS = message
            else:
                logger.debug('Нет новых статусов')
        except Exception as error:
            logger.error(error)
            message2 = str(error)
            if message2 != ERROR_CACHE_MESSAGE:
                send_message(bot, message2)
                ERROR_CACHE_MESSAGE = message2
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
