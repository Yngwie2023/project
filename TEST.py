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
    if log_file.endswith(".gz"):
        return opener_gz(log_file, pattern)
    else:
        return opener_default(log_file, pattern)

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

def main():
    
    """Настройка логирования с выводом в консоль"""
    basicConfig(format=u'[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S', level=INFO)

    info('Начало выполнения программы')

    log_dir = config["LOG_DIR"]
    for filename in os.listdir(log_dir):
        log_file = os.path.join(log_dir, filename)
        parsed_data = calculate(log_file)
        output_file = os.path.join(config["REPORT_DIR"], f"{filename}.json") 
        output_file_html = os.path.join(config["REPORT_DIR"], f"{filename}.html") 
         
        # write_to_json(parsed_data, output_file)
        html = data_for_html(parsed_data)
        make_report(html, output_file_html)
        info(f'Данные успешно записаны в {output_file} и {output_file_html}')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        info("Выполнение прервано пользователем")
    except Exception as e:
        exception('Глобальная ошибка')