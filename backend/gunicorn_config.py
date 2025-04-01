# gunicorn_config.py
import multiprocessing

# Привязка к сокету
bind = "0.0.0.0:5000"

# Количество рабочих процессов
# По рекомендациям: (2 x количество ядер) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Количество потоков для обработки запросов
threads = 2

# Тайм-ауты
timeout = 120
keepalive = 5

# Логирование
errorlog = "logs/gunicorn-error.log"
accesslog = "logs/gunicorn-access.log"
loglevel = "info"

# Демонизация процессов
daemon = False

# Использование pre-fork модели воркеров
preload_app = True