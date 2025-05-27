import os
import random
import time
from threading import Thread
from collections import deque
import numpy as np
from sklearn.linear_model import LinearRegression
import curses
from curses import textpad

# Конфигурация системы
NUM_SERVERS = 8
NUM_BACKUPS = 2
LOAD_THRESHOLD = 70  # Порог нагрузки 70%
COOLING_FACTOR = 0.7

# Инициализация серверов
server_stats = {}
for i in range(1, NUM_SERVERS + 1):
    server_stats[f'server{i}'] = {
        'cpu': random.randint(10, 50),
        'memory': random.randint(30, 70),
        'load': 0,
        'temp': 0,
        'status': 'normal',
        'history': deque(maxlen=60)
    }
for i in range(1, NUM_BACKUPS + 1):
    server_stats[f'backup{i}'] = {
        'cpu': random.randint(5, 30),
        'memory': random.randint(20, 50),
        'load': 0,
        'temp': 0,
        'status': 'standby',
        'history': deque(maxlen=60)
    }

class ServerMonitor(Thread):
    def __init__(self, server_name):
        Thread.__init__(self)
        self.server_name = server_name
        self.daemon = True
    
    def run(self):
        while True:
            try:
                # Генерация тестовых данных
                stats = server_stats[self.server_name]
                prev_cpu = stats['cpu']
                prev_mem = stats['memory']
                
                cpu_load = max(10, min(100, prev_cpu + random.randint(-15, 20)))
                memory_usage = max(30, min(90, prev_mem + random.randint(-10, 15)))
                temperature = 25 + cpu_load * 0.3 + random.randint(-3, 5)
                total_load = cpu_load * 0.6 + memory_usage * 0.3 + temperature * 0.1
                
                # Обновление статистики
                stats.update({
                    'cpu': cpu_load,
                    'memory': memory_usage,
                    'temp': temperature,
                    'load': total_load,
                    'status': 'overloaded' if total_load > LOAD_THRESHOLD else 
                             'high' if total_load > LOAD_THRESHOLD * 0.7 else 'normal'
                })
                stats['history'].append({
                    'time': time.time(),
                    'cpu': cpu_load,
                    'memory': memory_usage,
                    'temp': temperature,
                    'load': total_load
                })
                
                # Балансировка нагрузки
                if total_load > LOAD_THRESHOLD and not self.server_name.startswith('backup'):
                    self.redirect_load(total_load - LOAD_THRESHOLD)
                
                time.sleep(1)
            except Exception as e:
                print(f"Ошибка в мониторе {self.server_name}: {str(e)}")
                time.sleep(5)
    
    def redirect_load(self, amount):
        try:
            backup_servers = [s for s in server_stats if s.startswith('backup')]
            if backup_servers:
                target = min(backup_servers, key=lambda x: server_stats[x]['load'])
                print(f"Перенаправление {amount:.1f}% нагрузки с {self.server_name} на {target}")
                
                # Корректировка нагрузки
                for metric, factor in [('load', 0.8), ('cpu', 0.5), ('temp', 0.2)]:
                    server_stats[self.server_name][metric] = max(0, server_stats[self.server_name][metric] - amount * factor)
                
                for metric, factor in [('load', 0.7), ('cpu', 0.4), ('temp', 0.15)]:
                    server_stats[target][metric] = min(100, server_stats[target][metric] + amount * factor)
                
                server_stats[target]['status'] = 'active'
        except Exception as e:
            print(f"Ошибка при перенаправлении нагрузки: {str(e)}")

def predict_load(server_name):
    try:
        history = list(server_stats[server_name]['history'])
        if len(history) < 10:
            return 0
        
        X = np.array(range(len(history))).reshape(-1, 1)
        y = np.array([h['load'] for h in history])
        model = LinearRegression().fit(X, y)
        return model.predict(np.array([[len(history)], [len(history)+5], [len(history)+10]])).mean()
    except:
        return 0

def init_colors():
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)      # Перегружен
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)    # Высокая нагрузка
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)     # Норма
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)      # Активный
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)     # Резервный
    curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK)   # Заголовки
    curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)      # Границы

def draw_border(stdscr):
    stdscr.attron(curses.color_pair(7))
    stdscr.border()
    stdscr.attroff(curses.color_pair(7))

def draw_header(stdscr):
    stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
    title = " МОНИТОРИНГ ДАТА-ЦЕНТРА "
    stdscr.addstr(1, (curses.COLS - len(title)) // 2, title)
    
    subtitle = f"Порог нагрузки: {LOAD_THRESHOLD}% | Нажмите 'Q' для выхода"
    stdscr.addstr(2, (curses.COLS - len(subtitle)) // 2, subtitle)
    
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    stdscr.addstr(3, (curses.COLS - len(time_str)) // 2, time_str)
    stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)

def draw_stats(stdscr, row, servers_data):
    total_load = sum(s['load'] for s in servers_data) / len(servers_data)
    overloaded = sum(1 for s in servers_data if s['status'] == 'overloaded')
    
    stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
    stdscr.addstr(row, 2, "ОБЩАЯ СТАТИСТИКА:")
    stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
    
    stdscr.addstr(row + 1, 4, f"Средняя нагрузка: {total_load:.1f}%")
    stdscr.addstr(row + 2, 4, f"Перегруженных серверов: {overloaded}")
    stdscr.addstr(row + 3, 4, f"Всего серверов: {NUM_SERVERS} основных + {NUM_BACKUPS} резервных")

def draw_server_table(stdscr, start_row, servers_data):
    # Заголовок таблицы
    stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
    headers = ["СЕРВЕР", "CPU%", "ПАМЯТЬ%", "ТЕМП°C", "НАГРУЗКА%", "СТАТУС", "ПРОГНОЗ"]
    col_positions = [2, 14, 24, 34, 44, 56, 68]
    
    for i, header in enumerate(headers):
        stdscr.addstr(start_row, col_positions[i], header)
    
    stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
    
    # Данные серверов
    for i, server in enumerate(servers_data):
        row = start_row + 2 + i
        
        # Выбираем цвет в зависимости от статуса
        if server['status'] == 'overloaded':
            color = curses.color_pair(1) | curses.A_BOLD
        elif server['status'] == 'high':
            color = curses.color_pair(2) | curses.A_BOLD
        elif server['status'] == 'normal':
            color = curses.color_pair(3)
        elif server['status'] == 'active':
            color = curses.color_pair(4) | curses.A_BOLD
        else:  # standby
            color = curses.color_pair(5)
        
        # Выводим данные сервера
        stdscr.attron(color)
        stdscr.addstr(row, col_positions[0], server['name'])
        stdscr.addstr(row, col_positions[1], f"{server['cpu']:>5.1f}")
        stdscr.addstr(row, col_positions[2], f"{server['memory']:>7.1f}")
        stdscr.addstr(row, col_positions[3], f"{server['temp']:>6.1f}")
        stdscr.addstr(row, col_positions[4], f"{server['load']:>9.1f}")
        stdscr.addstr(row, col_positions[5], f"{server['status']:>10}")
        stdscr.addstr(row, col_positions[6], f"{server['prediction']:>7.1f}")
        stdscr.attroff(color)

def draw_dashboard(stdscr):
    curses.curs_set(0)  # Скрываем курсор
    stdscr.nodelay(1)   # Неблокирующий ввод
    init_colors()       # Инициализируем цвета
    
    # Увеличиваем шрифт (если терминал поддерживает)
    try:
        curses.resize_term(40, 120)  # Пытаемся увеличить размер терминала
    except:
        pass
    
    while True:
        stdscr.clear()
        
        # Рисуем интерфейс
        draw_border(stdscr)
        draw_header(stdscr)
        
        # Собираем данные
        servers_data = []
        for server in server_stats:
            stats = server_stats[server]
            servers_data.append({
                'name': server,
                'cpu': stats['cpu'],
                'memory': stats['memory'],
                'temp': stats['temp'],
                'load': stats['load'],
                'status': stats['status'],
                'prediction': predict_load(server)
            })
        
        # Сортируем серверы
        servers_data.sort(key=lambda x: (x['name'].startswith('backup'), x['name']))
        
        # Рисуем таблицу серверов
        draw_server_table(stdscr, 6, servers_data)
        
        # Рисуем статистику
        draw_stats(stdscr, 6 + len(servers_data) + 4, servers_data)
        
        # Проверка нажатия клавиши 'q' для выхода
        key = stdscr.getch()
        if key in (ord('q'), ord('Q')):
            break
        
        stdscr.refresh()
        time.sleep(1)  # Обновление каждую секунду

def main():
    # Запуск мониторинга для всех серверов
    for server in server_stats:
        ServerMonitor(server).start()
    
    # Запуск терминального интерфейса
    try:
        curses.wrapper(draw_dashboard)
    except KeyboardInterrupt:
        print("\nМониторинг остановлен")

if __name__ == '__main__':
    main()
