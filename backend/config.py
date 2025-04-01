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
    CORS_ORIGINS_DEV = ['http://localhost:8080', 'http://localhost:5000', 'http://localhost:3000']
    CORS_ORIGINS_PROD = ['https://blog.666s.dev']

    JWT_ACCESS_TOKEN_EXPIRES = 30 * 60  # 30 minutes in seconds
    JWT_REFRESH_TOKEN_EXPIRES = 15 * 24 * 60 * 60  # 15 days in seconds

    # Настройки для загрузки файлов
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    LOG_LEVEL = logging.DEBUG


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    LOG_LEVEL = logging.INFO

    # Обязательно использовать переменные окружения для секретных ключей
    @property
    def SECRET_KEY(self):
        key = os.environ.get('SECRET_KEY')
        if not key:
            raise ValueError("SECRET_KEY must be set in production environment")
        return key

    @property
    def JWT_SECRET_KEY(self):
        key = os.environ.get('JWT_SECRET_KEY')
        if not key:
            raise ValueError("JWT_SECRET_KEY must be set in production environment")
        return key

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