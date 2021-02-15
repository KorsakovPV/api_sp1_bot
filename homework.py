import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(filename='example.log', level=logging.DEBUG)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
YANDEX_WEATHER_KEY = os.getenv('YANDEX_WEATHER_KEY')
# https://spys.one/proxies/
# proxy = telegram.utils.request.Request(proxy_url='socks5://47.110.49.177:1080')
# bot = telegram.Bot(token=TELEGRAM_TOKEN, request=proxy)
bot = telegram.Bot(token=TELEGRAM_TOKEN)
base_url_praktikum = 'https://praktikum.yandex.ru/api/user_api/'

base_url_yndex_weather = 'https://api.weather.yandex.ru/v2/forecast/'


def parse_homework_status(homework):
    homework_name = homework.get('homework_name')
    answer = {'rejected': 'К сожалению в работе нашлись ошибки.',
              'approved': ('Ревьюеру всё понравилось, можно '
                           'приступать к следующему уроку.')
              }
    homework_status = homework.get('status')
    if homework_status in ('rejected', 'approved'):
        verdict = answer[homework_status]
        return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'
    else:
        logging.error(
            '\tInvalid response from the server. The server responded "{}".'.format(
                homework_status))
        return 'Неправильный ответ от сервера.'


def get_homework_statuses(current_timestamp):
    if current_timestamp is None:
        current_timestamp = int(time.time())
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    url = '{}{}'.format(base_url_praktikum, 'homework_statuses/')
    try:
        homework_statuses = requests.get(url,
                                         params={
                                             'from_date': current_timestamp},
                                         headers=headers)
    except requests.exceptions.Timeout:
        logging.error("\tVery Slow Internet Connection.")
        return {}
    except requests.exceptions.ConnectionError:
        logging.error("\tNetwork Unavailable. Check your connection.")
        return {}
    except requests.exceptions.MissingSchema:
        logging.error("\t503 Service Unavailable. Retrying download ... ")
        return {}
    return homework_statuses.json()


def send_message(message):
    return bot.send_message(chat_id=CHAT_ID, text=message)


class YndexWeatherAPI:
    def __init__(self):
        self.cities = {'Обь': ('54.998104', '82.69529'),
                       'Шерегеш': ('52.921485125515176', '87.98940216931146')}

    def get_cities(self):
        return ', '.join([city for city in self.cities])

    def get_api_city_weather(self, city):
        lat, lon = self.cities.get(city)
        headers = {'X-Yandex-API-Key': f'{YANDEX_WEATHER_KEY}'}
        try:
            weather = requests.get(base_url_yndex_weather,
                                   params={'lat': lat,
                                           'lon': lon},
                                   headers=headers)
        except requests.exceptions.Timeout:
            logging.error("\tVery Slow Internet Connection.")
            return {}
        except requests.exceptions.ConnectionError:
            logging.error("\tNetwork Unavailable. Check your connection.")
            return {}
        except requests.exceptions.MissingSchema:
            logging.error("\t503 Service Unavailable. Retrying download ... ")
            return {}
        return weather.json().get('fact').get('temp')

    def get_city_weather(self, city):
        if city in self.cities.keys():
            return self.get_api_city_weather(city)
        else:
            return 'Не верно указан город.'


def main():
    current_timestamp = int(time.time())

    yandex_weather_api = YndexWeatherAPI()

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get('message') == 'Учетные данные не были ' \
                                              'предоставлены.':
                send_message('Yandex praktikum. Учетные данные не были '
                             'предоставлены.')
            if new_homework.get('homeworks'):
                send_message(
                    parse_homework_status(new_homework.get('homeworks')[0]))
            current_timestamp = new_homework.get('current_date')

            # send_message('Доступные города {}'.format(yandex_weather_api.get_cities()))
            # send_message(yandex_weather_api.get_city_weather('Обь'))

            for item in bot.get_updates():
                mesage = item['message']['text']
                if mesage in yandex_weather_api.cities.keys():
                    send_message('Погода в {} {}'.format(mesage, yandex_weather_api.get_city_weather(mesage)))
                # send_message(mesage)


            time.sleep(300)

        except Exception as e:
            print(f'Бот упал с ошибкой: {e}')
            time.sleep(5)
            continue


if __name__ == '__main__':
    main()
