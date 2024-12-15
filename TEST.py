import re
import json
import os
import gzip
from statistics import median
from logging import *
from html import *
from pathlib import Path
from string import Template


config = {
        "REPORT_SIZE": 1000,
        "REPORT_DIR": "./reports",
        "LOG_DIR": "./log"
    }

def init_config(config):
    try:
        with open('config.json', 'r') as config_file:
            config_data = json.load(config_file)
        return config_data
    except: 
        return config


def opener_gz(log_file, pattern):
    with gzip.open(log_file, 'rt', encoding='utf-8') as f:
            for line in f:
                match = pattern.match(line)
                if match:
                    yield (match.group('request'), float(match.group('time')))

def opener_default(log_file, pattern):
    with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                match = pattern.match(line)
                if match:
                    yield (match.group('request'), float(match.group('time')))

def log_parser(log_file):
    """Парсит файл логов nginx и возвращает генератор пар (URL, время обработки)."""
    pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+) -  - \[(.+)\] "(.+) (?P<request>.+) (.+)" '
                         r'(\d+) (\d+) \"(.+)\" "(.+)" "(.+)" "(.+)" (.+) (?P<time>.+)')
    
    """Проверка лог файла на формат .gz и обработка ошибки на отсутствие файла в каталоге"""
    
    return opener_gz(log_file, pattern) if log_file.endswith(".gz") else opener_default(log_file, pattern)

def calculate(log_file):
    parsed_data = {}
    total_requests = 0
    total_time = 0.0
    for url, time in log_parser(log_file):
        if url not in parsed_data:
            parsed_data[url] = {
                'count': 0,
                'time_sum': 0.0,
                'times': []
            }
        parsed_data[url]['count'] += 1
        parsed_data[url]['time_sum'] += time
        parsed_data[url]['times'].append(time)
        total_requests += 1
        total_time += time
    
    for url, stats in parsed_data.items():
        stats['count_pers'] = round((stats['count'] / total_requests) * 100, 3)
        stats['time_pers'] = round((stats['time_sum'] / total_time) * 100, 3)
        stats['time_avg'] = round(stats['time_sum'] / stats['count'], 3)
        stats['time_max'] = round(max(stats['times']), 3)
        stats['time_med'] = round(median(stats['times']), 3)

        del parsed_data[url]['times'] # Удаление вспомогательного списка 'times'
    return parsed_data

def data_for_html(parsed_data):
    result = []

    for url, values in parsed_data.items():
            count = values['count']
            count_pers = values['count_pers']
            time_sum = round(values['time_sum'], 3)
            time_pers = values['time_pers']
            time_avg = values['time_avg']
            time_max = values['time_max']
            time_med = values['time_med']


            result.append(
            {'url': url, 
             'count': count, 
             'count_pers': count_pers, 
             'time_sum': time_sum, 
             'time_pers': time_pers,
             'time_avg': time_avg, 
             'time_max': time_max, 
             'time_med': time_med})
    return result

def make_report(result, output_file_html):
    """Запись в HTML"""
    template = Template(Path('report.html').read_text(encoding='utf-8'))
    dictionary = template.safe_substitute(table_json=json.dumps(result))
    Path(output_file_html).write_text(dictionary, encoding='utf-8')

# def write_to_json(parsed_data, output_file):
#     """Запись данных в JSON"""
#     with open(output_file, 'w') as f:
#         json.dump(parsed_data, f, indent=4)

def get_latest_logfile(log_dir):
    """Находит последний лог-файл в директории, используя дату из имени файла."""
    latest_file = None
    latest_date = 0

    for filename in os.listdir(log_dir):
        match = re.match(r"nginx-access-ui\.log-(\d{8})(\_SHORT|\.gz)?$", filename)  #Парсинг имени файла
        if match:
            try:
                date = int(match.group(1))
                if date > latest_date:
                    latest_date = date
                    latest_file = os.path.join(log_dir, filename)
            except ValueError:
                exception(f"Не удалось распарсить дату из имени файла: {filename}")

    if latest_file is None:
        error("Не найдено файлов логов, соответствующих шаблону")
        return None

    info(f"Найден последний лог-файл: {latest_file}")
    return latest_file

def main():
    
    """Настройка логирования с выводом в консоль"""
    basicConfig(format=u'[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S', level=INFO)

    info('Начало выполнения программы')

    # log_dir = config["LOG_DIR"]
    log_dir = init_config(config)["LOG_DIR"]
    latest_logfile = get_latest_logfile(log_dir)

    if latest_logfile:
        parsed_data = calculate(latest_logfile)
        filename = os.path.basename(latest_logfile) #Извлекаем имя файла без пути
        output_file = os.path.join(config["REPORT_DIR"], f"{filename}.json")
        output_file_html = os.path.join(config["REPORT_DIR"], f"{filename}.html")

        html = data_for_html(parsed_data)
        make_report(html, output_file_html)
        # write_to_json(html, output_file)
        info(f'Данные успешно записаны в {output_file} и {output_file_html}')
    else:
        info("Обработка лог-файлов пропущена, т.к. подходящих файлов не найдено.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        info("Выполнение прервано пользователем")
    except Exception as e:
        exception('Глобальная ошибка')