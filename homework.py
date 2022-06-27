import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

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

logging.basicConfig(
    level=logging.INFO,
    filename='homework.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception as error:
        logger.error(f'Ошибка отправки сообщения в Telegramm: {error}')


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        hw_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'Ошибка при запросе: {error}')
    if hw_status.status_code != HTTPStatus.OK:
        status_code = hw_status.status_code
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    try:
        return hw_status.json()
    except ValueError:
        logger.error('Ошибка парсинга')


def check_response(response):
    """проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API,
     приведенный к типам данных Python.
     Если ответ API соответствует ожиданиям,
     то функция должна вернуть список домашних работ (он может быть и пустым),
      доступный в ответе API по ключу 'homeworks'"""

    try:
        hw_list = response['homeworks']
    except KeyError:
        logger.error('Ошибка словаря по ключу homeworks')
        raise KeyError('Ошибка словаря по ключу homeworks')
    try:
        homework = hw_list[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """извлекает из информации о конкретной домашней работе статус этой работы.
     В качестве параметра функция получает только один элемент
      из списка домашних работ.
      В случае успеха, функция возвращает подготовленную
       для отправки в Telegram строку,
      содержащую один из вердиктов словаря HOMEWORK_STATUSES"""

    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """проверяет доступность переменных окружения.
     которые необходимы для работы программы.
     Если отсутствует хотя бы одна переменная окружения — функция
     должна вернуть False, иначе — True."""

    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Функция main(): в ней описана основная логика работы программы.
     Все остальные функции должны запускаться из неё.
     Последовательность действий должна быть примерно такой:
     Сделать запрос к API.
     Проверить ответ.
     Если есть обновления — получить статус работы из обновления
     и отправить сообщение в Telegram.
     Подождать некоторое время и сделать новый запрос."""

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    STATUS = ''
    ERROR_CACHE_MESSAGE = ''
    if not check_tokens():
        logger.critical('Ошибка переменных окружения')
        raise Exception('Ошибка переменных окружения')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != STATUS:
                send_message(bot, message)
                STATUS = message
            time.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(error)
            message2 = str(error)
            if message2 != ERROR_CACHE_MESSAGE:
                send_message(bot, message2)
                ERROR_CACHE_MESSAGE = message2
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
