import sqlite3
import uuid
import imghdr

from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
from io import BytesIO

from backend.models.user import User
from backend.models.base import commit_db, get_db, query_db


class Image:
    """Модель для работы с изображениями"""

    @staticmethod
    def allowed_file(filename):
        """Проверка допустимости расширения файла"""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']

    @staticmethod
    def generate_unique_filename(filename):
        """Генерация уникального имени файла"""
        # Получаем безопасное имя файла
        secure_name = secure_filename(filename)
        # Получаем расширение
        ext = secure_name.rsplit('.', 1)[1].lower() if '.' in secure_name else ''
        # Генерируем уникальное имя с UUID
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        return unique_name

    @staticmethod
    def validate_image(file_data):
        """Проверяет, что файл действительно является изображением"""
        # Проверка типа файла по его содержимому
        img_type = imghdr.what(None, file_data)
        if img_type not in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
            raise ValueError("Файл не является допустимым изображением")
        return True

    @staticmethod
    def preprocess_image(file_data, max_size=None, target_file_size=None):
        """
        Предобработка изображения:
        1. Проверяет, что это действительно изображение
        2. Изменяет размер, если он превышает максимальный
        3. Оптимизирует размер файла, если он превышает целевой
        4. Удаляет метаданные для безопасности
        """
        try:
            if max_size is None:
                max_size = current_app.config['MAX_IMAGE_DIMENSIONS']

            if target_file_size is None:
                target_file_size = current_app.config['MAX_IMAGE_SIZE']

            # Валидация изображения
            Image.validate_image(file_data)

            # Открываем изображение с помощью PIL
            img = PILImage.open(BytesIO(file_data))

            # Удаляем метаданные EXIF для безопасности
            if hasattr(img, '_getexif') and img._getexif():
                img = PILImage.new(img.mode, img.size)

            # Преобразуем в RGB, если это необходимо (для CMYK или других форматов)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')

            # Изменяем размер, если нужно
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, PILImage.LANCZOS)

            # Начальное качество
            quality = 95
            output = BytesIO()

            # Сохраняем с постепенным уменьшением качества, пока размер не станет приемлемым
            while quality >= 70:  # Минимальное качество 70%
                output = BytesIO()
                img.save(output, format=img.format or 'JPEG', optimize=True, quality=quality)
                output.seek(0)
                data = output.getvalue()

                # Если размер меньше целевого или качество уже минимальное, выходим из цикла
                if len(data) <= target_file_size or quality <= 70:
                    break

                # Уменьшаем качество на 5% за итерацию
                quality -= 5

            # Если после всех оптимизаций файл все еще слишком большой
            if len(data) > target_file_size:
                raise ValueError(
                    f"Не удалось оптимизировать изображение до требуемого размера (максимум {target_file_size // 1024 // 1024}MB)")

            return data
        except Exception as e:
            raise ValueError(f"Ошибка обработки изображения: {str(e)}")

    @staticmethod
    def save_file(file, author_id, post_id=None):
        """Сохранение файла изображения в базу данных"""

        if not file or not Image.allowed_file(file.filename):
            raise ValueError("Недопустимый формат файла")

        # Читаем данные файла
        file_data = file.read()

        try:
            # Предобработка изображения
            processed_data = Image.preprocess_image(file_data)

            # Генерируем уникальное имя файла
            unique_filename = Image.generate_unique_filename(file.filename)

            # Получаем тип файла
            file_type = file.content_type if hasattr(file, 'content_type') else "image/jpeg"

            # URL путь для доступа через API
            url_path = f"/api/images/data/{unique_filename}"

            # Сохраняем в базу данных
            db = get_db()
            now = datetime.now().isoformat()

            db.execute(
                '''INSERT INTO images 
                   (filename, original_filename, filetype, filesize, post_id, author_id, upload_date, url_path, image_data) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                [unique_filename, file.filename, file_type, len(processed_data),
                 post_id, author_id, now, url_path, sqlite3.Binary(processed_data)]
            )
            commit_db()

            # Получаем ID последнего добавленного изображения
            image_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            return Image.get_by_id(image_id)
        except Exception as e:
            current_app.logger.error(f"Ошибка сохранения изображения: {str(e)}")
            raise

    @staticmethod
    def get_image_data(filename):
        """Получить данные изображения из БД"""
        image = query_db('SELECT filetype, image_data FROM images WHERE filename = ?', [filename], one=True)
        if not image:
            return None
        return {
            'data': image['image_data'],
            'filetype': image['filetype']
        }

    @staticmethod
    def get_by_id(image_id):
        """Получить информацию об изображении по ID"""
        return query_db(
            'SELECT * FROM images WHERE id = ?',
            [image_id], one=True
        )

    @staticmethod
    def get_by_post(post_id):
        """Получить все изображения для поста"""
        return query_db(
            'SELECT * FROM images WHERE post_id = ? ORDER BY upload_date DESC',
            [post_id]
        )

    @staticmethod
    def get_by_author(author_id, limit=None):
        """Получить изображения пользователя"""
        query = '''
            SELECT id, filename, original_filename, filetype, filesize, 
                   post_id, author_id, upload_date, url_path
            FROM images 
            WHERE author_id = ? 
            ORDER BY upload_date DESC
        '''

        if limit:
            query += f' LIMIT {limit}'

        return query_db(query, [author_id])

    @staticmethod
    def delete(image_id, author_id=None):
        """Удалить изображение"""

        # Получаем информацию об изображении
        image = Image.get_by_id(image_id)
        if not image:
            return False

        # Проверяем права доступа
        if author_id is not None and image['author_id'] != author_id:
            return False

        # Удаляем запись из базы данных
        db = get_db()
        db.execute('DELETE FROM images WHERE id = ?', [image_id])
        commit_db()

        return True

    @staticmethod
    def update_post_id(image_id, post_id, author_id=None):
        """Привязать изображение к посту"""
        # Получаем информацию об изображении
        image = Image.get_by_id(image_id)
        if not image:
            return False

        # Проверяем права доступа
        if author_id is not None and image['author_id'] != author_id:
            return False

        # Обновляем запись в базе данных
        db = get_db()
        db.execute(
            'UPDATE images SET post_id = ? WHERE id = ?',
            [post_id, image_id]
        )
        commit_db()

        return True


    @staticmethod
    def can_user_manage_image(image_id, user_id):
        """Check if user can manage an image (owner or admin)"""
        # Admin can manage any image
        if User.is_admin(user_id):
            return True

        image = Image.get_by_id(image_id)
        if not image:
            return False

        return image['author_id'] == user_id