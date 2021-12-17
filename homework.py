import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, Updater

from exceptions import ResponseStatusError, SendMessageError

load_dotenv()

logging.basicConfig(
    format='%(asctime)s, %(name)s, %(levelname)s, %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    encoding='UTF-8'
)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

TELEGRAM_RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(
            TELEGRAM_CHAT_ID,
            message
        )
    except Exception:
        logging.error('ERROR IN SENDING MESSAGE')
        raise SendMessageError('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Запрос к API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except ValueError:
        logging.error('ERROR IN API ANSWER')
    if response.status_code != 200:
        raise ResponseStatusError('Статус страницы не 200')
    if response is None:
        raise TypeError('Status = None')
    logging.info('API ANSWER IS OK')
    return response.json()


def check_response(response):
    """Проверка ответа."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ API - не словарь'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Домашка пришла не в виде списка'
        )
    if 'homeworks' not in response:
        raise KeyError(
            'Неправильный ключ домашки'
        )
    if response is None:
        raise TypeError('Response = None')
    logging.info('RESPONSE IS OK')
    return response.get('homeworks')


def parse_status(homework):
    """Статус домашки."""
    if 'homework_name' not in homework:
        message = 'Unknown homework_name of homework'
        logging.error(message)
        raise KeyError(message)
    if 'status' not in homework:
        message = 'Unknown status of homework'
        logging.error(message)
        raise KeyError(message)
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Unknown homework_status'
        logging.error(message)
        raise KeyError(message)
    homework_name = homework['homework_name']
    verdict = HOMEWORK_STATUSES.get(homework_status)
    logging.info('PARSE STATUS IS OK')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка Токенов."""
    variables = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logging.info('TOKENS ARE OK')
        return True
    if None in variables:
        logging.error(f'Не хватает переменных: {variables}')
        return False


def main():
    """Основная логика работы бота."""
    updater = Updater(TELEGRAM_TOKEN)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    button = ReplyKeyboardMarkup([['/homework']], resize_keyboard=True)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            for homework in check_response(response):
                send_message(bot, parse_status(homework))
            current_timestamp = int(time.time())
            time.sleep(TELEGRAM_RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            bot.send_message(TELEGRAM_CHAT_ID, message, reply_markup=button)
            time.sleep(TELEGRAM_RETRY_TIME)

        updater.dispatcher.add_handler(
            CommandHandler('start', send_message)
        )
        updater.dispatcher.add_handler(
            CommandHandler('homework', parse_status)
        )
        updater.start_polling()


if __name__ == '__main__':
    check_tokens()
    main()
