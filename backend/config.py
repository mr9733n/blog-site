import logging
import os
import secrets


class Config:
    """Базовая конфигурация приложения"""
    # Секретный ключ для подписи сессий и токенов
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or secrets.token_hex(16)

    # Настройки базы данных
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

    # Настройки CORS
    CORS_ORIGINS = ['http://localhost:8080', 'http://localhost:5000', 'http://localhost:3000']

    JWT_ACCESS_TOKEN_EXPIRES = 30 * 60  # 30 minutes in seconds
    JWT_REFRESH_TOKEN_EXPIRES = 15 * 24 * 60 * 60  # 15 days in seconds


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    LOG_LEVEL = logging.DEBUG

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    LOG_LEVEL = logging.INFO
    # В продакшене обязательно установите сложные секретные ключи через переменные окружения


# Выбор конфигурации в зависимости от переменной окружения
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Получить активную конфигурацию"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config[env]