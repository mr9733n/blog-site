import sqlite3
import os
import uuid
from flask import g
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
from io import BytesIO
import imghdr
from flask import send_file

# Функции для работы с базой данных
def get_db():
    """Получить соединение с базой данных"""
    db = getattr(g, '_database', None)
    if db is None:
        from app import app
        db = g._database = sqlite3.connect(app.config['DATABASE_PATH'])
        db.row_factory = sqlite3.Row
    return db


def query_db(query, args=(), one=False):
    """Выполнить запрос к базе данных"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def commit_db():
    """Зафиксировать изменения в базе данных"""
    get_db().commit()


class User:
    """Модель пользователя"""

    def is_admin(user_id):
        """Check if a user has admin privileges"""
        # Simple check - user with ID 1 is admin
        return int(user_id) == 1

    @staticmethod
    def get_by_id(user_id):
        """Получить пользователя по ID"""
        return query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)

    @staticmethod
    def get_by_username(username):
        """Получить пользователя по имени пользователя"""
        return query_db('SELECT * FROM users WHERE username = ?', [username], one=True)

    @staticmethod
    def create(username, email, password):
        """Создать нового пользователя"""
        # Проверка наличия пользователя
        if User.get_by_username(username):
            raise ValueError("Пользователь с таким именем уже существует")

        # Проверка наличия email
        if query_db('SELECT * FROM users WHERE email = ?', [email], one=True):
            raise ValueError("Пользователь с таким email уже существует")

        # Хеширование пароля и сохранение пользователя
        password_hash = generate_password_hash(password)
        db = get_db()
        db.execute(
            'INSERT INTO users (username, password, email, created_at) VALUES (?, ?, ?, ?)',
            [username, password_hash, email, datetime.now().isoformat()]
        )
        commit_db()
        return User.get_by_username(username)

    @staticmethod
    def verify_password(username, password):
        """Проверить пароль пользователя"""
        user = User.get_by_username(username)
        if not user:
            return False
        return check_password_hash(user['password'], password)

    @staticmethod
    def get_token_lifetime(user_id):
        """Get token lifetime setting for a user (in seconds)"""
        try:
            setting = query_db(
                'SELECT token_lifetime FROM user_settings WHERE user_id = ?',
                [user_id], one=True
            )
            if setting:
                return setting['token_lifetime']

            # Create default setting if not exists
            db = get_db()
            from app import app
            default_lifetime = app.config['JWT_ACCESS_TOKEN_EXPIRES']
            db.execute(
                'INSERT INTO user_settings (user_id, token_lifetime) VALUES (?, ?)',
                [user_id, default_lifetime]
            )
            commit_db()
            return default_lifetime
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                # Таблица не существует, используем значение по умолчанию
                from app import app
                return app.config['JWT_ACCESS_TOKEN_EXPIRES']
            raise  # Пробрасываем другие ошибки

    @staticmethod
    def update_token_settings(user_id, token_lifetime, refresh_token_lifetime):
        """Update token lifetime settings for a user"""
        db = get_db()
        # Проверяем, существуют ли настройки
        setting = query_db(
            'SELECT * FROM user_settings WHERE user_id = ?',
            [user_id], one=True
        )

        if setting:
            db.execute(
                'UPDATE user_settings SET token_lifetime = ?, refresh_token_lifetime = ? WHERE user_id = ?',
                [token_lifetime, refresh_token_lifetime, user_id]
            )
        else:
            db.execute(
                'INSERT INTO user_settings (user_id, token_lifetime, refresh_token_lifetime) VALUES (?, ?, ?)',
                [user_id, token_lifetime, refresh_token_lifetime]
            )
        commit_db()
        return True


    @staticmethod
    def get_all_users():
        """Получить список всех пользователей"""
        return query_db('SELECT id, username, email, created_at FROM users ORDER BY id')


    @staticmethod
    def update_user(user_id, username=None, email=None, password=None):
        """Обновить данные пользователя"""
        db = get_db()
        update_parts = []
        params = []

        if username:
            # Проверка уникальности нового имени пользователя
            existing = query_db('SELECT id FROM users WHERE username = ? AND id != ?',
                                [username, user_id], one=True)
            if existing:
                raise ValueError("Пользователь с таким именем уже существует")
            update_parts.append("username = ?")
            params.append(username)

        if email:
            # Проверка уникальности нового email
            existing = query_db('SELECT id FROM users WHERE email = ? AND id != ?',
                                [email, user_id], one=True)
            if existing:
                raise ValueError("Пользователь с таким email уже существует")
            update_parts.append("email = ?")
            params.append(email)

        if password:
            password_hash = generate_password_hash(password)
            update_parts.append("password = ?")
            params.append(password_hash)

        if not update_parts:
            return False  # Нечего обновлять

        # Формируем SQL запрос
        query = f"UPDATE users SET {', '.join(update_parts)} WHERE id = ?"
        params.append(user_id)

        # Выполняем запрос
        db.execute(query, params)
        commit_db()

        return True


    @staticmethod
    def toggle_user_block(user_id, blocked_status):
        """Заблокировать или разблокировать пользователя"""
        # Проверяем, что не блокируем админа (пользователя с id=1)
        if int(user_id) == 1:
            raise ValueError("Невозможно заблокировать администратора")

        # Проверяем, существует ли таблица user_status
        db = get_db()
        try:
            # Проверяем существование таблицы user_status
            db.execute("SELECT 1 FROM user_status LIMIT 1")
        except sqlite3.OperationalError:
            # Таблица не существует, создаем её
            db.execute('''
                CREATE TABLE IF NOT EXISTS user_status (
                    user_id INTEGER PRIMARY KEY,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    blocked_at TEXT,
                    blocked_reason TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            commit_db()

        # Теперь работаем с таблицей
        if blocked_status:
            # Блокируем пользователя
            now = datetime.now().isoformat()
            db.execute('''
                INSERT INTO user_status (user_id, is_blocked, blocked_at) 
                VALUES (?, 1, ?) 
                ON CONFLICT(user_id) DO UPDATE SET is_blocked = 1, blocked_at = ?
            ''', [user_id, now, now])
        else:
            # Разблокируем пользователя
            db.execute('''
                INSERT INTO user_status (user_id, is_blocked, blocked_at) 
                VALUES (?, 0, NULL) 
                ON CONFLICT(user_id) DO UPDATE SET is_blocked = 0, blocked_at = NULL
            ''', [user_id])

        commit_db()
        return True


    @staticmethod
    def is_user_blocked(user_id):
        """Проверить, заблокирован ли пользователь"""
        try:
            status = query_db(
                'SELECT is_blocked FROM user_status WHERE user_id = ?',
                [user_id], one=True
            )
            return status and status['is_blocked'] == 1
        except sqlite3.OperationalError:
            # Таблица user_status не существует, значит никто не заблокирован
            return False


    @staticmethod
    def get_user_with_status(user_id):
        """Получить информацию о пользователе вместе со статусом блокировки"""
        user = User.get_by_id(user_id)
        if not user:
            return None

        user_dict = dict(user)

        try:
            status = query_db(
                'SELECT is_blocked, blocked_at, blocked_reason FROM user_status WHERE user_id = ?',
                [user_id], one=True
            )

            if status:
                user_dict['is_blocked'] = status['is_blocked'] == 1
                user_dict['blocked_at'] = status['blocked_at']
                user_dict['blocked_reason'] = status['blocked_reason']
            else:
                user_dict['is_blocked'] = False
                user_dict['blocked_at'] = None
                user_dict['blocked_reason'] = None
        except sqlite3.OperationalError:
            # Таблица не существует
            user_dict['is_blocked'] = False
            user_dict['blocked_at'] = None
            user_dict['blocked_reason'] = None

        return user_dict


    @staticmethod
    def get_all_users_with_status():
        """Получить список всех пользователей с информацией о блокировке"""
        users = User.get_all_users()
        users_list = [dict(user) for user in users]

        try:
            # Пытаемся получить статусы пользователей
            statuses = query_db('SELECT user_id, is_blocked, blocked_at, blocked_reason FROM user_status')
            statuses_dict = {status['user_id']: status for status in statuses}

            # Добавляем информацию о блокировке к каждому пользователю
            for user in users_list:
                user_id = user['id']
                if user_id in statuses_dict:
                    status = statuses_dict[user_id]
                    user['is_blocked'] = status['is_blocked'] == 1
                    user['blocked_at'] = status['blocked_at']
                    user['blocked_reason'] = status['blocked_reason']
                else:
                    user['is_blocked'] = False
                    user['blocked_at'] = None
                    user['blocked_reason'] = None
        except sqlite3.OperationalError:
            # Таблица user_status не существует
            # Задаём всем статус "не заблокирован"
            for user in users_list:
                user['is_blocked'] = False
                user['blocked_at'] = None
                user['blocked_reason'] = None

        return users_list

class Post:
    """Модель поста блога"""

    @staticmethod
    def get_all(limit=None, offset=None):
        """Получить все посты"""
        query = '''
            SELECT posts.*, users.username 
            FROM posts 
            JOIN users ON posts.author_id = users.id 
            ORDER BY created_at DESC
        '''

        if limit is not None and offset is not None:
            query += f' LIMIT {limit} OFFSET {offset}'

        return query_db(query)

    @staticmethod
    def get_by_id(post_id):
        """Получить пост по ID"""
        return query_db(
            '''SELECT posts.*, users.username 
               FROM posts JOIN users ON posts.author_id = users.id 
               WHERE posts.id = ?''',
            [post_id], one=True
        )

    @staticmethod
    def create(title, content, author_id):
        """Создать новый пост"""
        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            'INSERT INTO posts (title, content, author_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
            [title, content, author_id, now, now]
        )
        commit_db()

        # Получить ID последней вставленной записи
        post_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        return Post.get_by_id(post_id)

    @staticmethod
    def update(post_id, title, content):
        """Обновить пост"""
        db = get_db()
        db.execute(
            'UPDATE posts SET title = ?, content = ?, updated_at = ? WHERE id = ?',
            [title, content, datetime.now().isoformat(), post_id]
        )
        commit_db()
        return Post.get_by_id(post_id)

    @staticmethod
    def delete(post_id):
        """Удалить пост"""
        db = get_db()
        db.execute('DELETE FROM posts WHERE id = ?', [post_id])
        commit_db()
        return True

    @staticmethod
    def get_by_author(author_id):
        """Получить посты определенного автора"""
        return query_db(
            '''SELECT posts.*, users.username 
               FROM posts JOIN users ON posts.author_id = users.id 
               WHERE posts.author_id = ? 
               ORDER BY created_at DESC''',
            [author_id]
        )

    @staticmethod
    def get_post_comments(post_id):
        """Получить комментарии к посту"""
        return query_db(
            '''SELECT comments.*, users.username 
               FROM comments 
               JOIN users ON comments.author_id = users.id 
               WHERE comments.post_id = ? 
               ORDER BY comments.created_at ASC''',
            [post_id]
        )

    def can_user_edit_post(post_id, user_id):
        """Check if user can edit a post (owner or admin)"""
        # Admin can edit any post
        if User.is_admin(user_id):
            return True

        # Regular check for post owner
        post = Post.get_by_id(post_id)
        if not post:
            return False
        return post['author_id'] == user_id


class Image:
    """Модель для работы с изображениями"""

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DIMENSIONS = (1920, 1080)  # Maximum width and height

    @staticmethod
    def allowed_file(filename):
        """Проверка допустимости расширения файла"""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in Image.ALLOWED_EXTENSIONS

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
        if img_type not in ['jpeg', 'png', 'gif', 'webp']:
            raise ValueError("Файл не является допустимым изображением")
        return True

    @staticmethod
    def preprocess_image(file_data, max_size=MAX_DIMENSIONS):
        """
        Предобработка изображения:
        1. Проверяет, что это действительно изображение
        2. Изменяет размер, если он превышает максимальный
        3. Удаляет метаданные для безопасности
        """
        try:
            # Валидация изображения
            Image.validate_image(file_data)

            # Открываем изображение с помощью PIL
            img = PILImage.open(BytesIO(file_data))

            # Преобразуем в RGB, если это необходимо (для CMYK или других форматов)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')

            # Изменяем размер, если нужно
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, PILImage.LANCZOS)

            # Сохраняем в BytesIO и получаем обработанные данные
            output = BytesIO()
            img.save(output, format=img.format or 'JPEG', optimize=True)
            output.seek(0)
            return output.getvalue()
        except Exception as e:
            raise ValueError(f"Ошибка обработки изображения: {str(e)}")

    @staticmethod
    def save_file(file, author_id, post_id=None):
        """Сохранение файла изображения в базу данных"""
        from app import app, logger

        if not file or not Image.allowed_file(file.filename):
            raise ValueError("Недопустимый формат файла")

        # Читаем данные файла
        file_data = file.read()

        # Проверяем размер файла
        if len(file_data) > Image.MAX_IMAGE_SIZE:
            raise ValueError(f"Размер файла превышает допустимый (максимум {Image.MAX_IMAGE_SIZE // 1024 // 1024}MB)")

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
            logger.error(f"Ошибка сохранения изображения: {str(e)}")
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
        from app import app

        # Получаем информацию об изображении
        image = Image.get_by_id(image_id)
        if not image:
            return False

        # Проверяем права доступа
        if author_id is not None and image['author_id'] != author_id:
            return False

        # Удаляем физический файл
        file_path = os.path.join(app.static_folder, 'uploads', image['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)

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


# Класс SavedPost
class SavedPost:
    """Модель для сохраненных постов"""

    @staticmethod
    def is_post_saved_by_user(user_id, post_id):
        """Проверить, сохранён ли пост пользователем"""
        return query_db(
            'SELECT 1 FROM saved_posts WHERE user_id = ? AND post_id = ?',
            [user_id, post_id],
            one=True
        ) is not None

    @staticmethod
    def save_post(user_id, post_id):
        """Добавить пост в сохранённые"""
        # Проверяем, не сохранен ли уже пост
        if SavedPost.is_post_saved_by_user(user_id, post_id):
            return False

        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            'INSERT INTO saved_posts (user_id, post_id, saved_at) VALUES (?, ?, ?)',
            [user_id, post_id, now]
        )
        commit_db()
        return True

    @staticmethod
    def unsave_post(user_id, post_id):
        """Удалить пост из сохранённых"""
        # Проверяем, существует ли запись
        if not SavedPost.is_post_saved_by_user(user_id, post_id):
            return False

        db = get_db()
        db.execute(
            'DELETE FROM saved_posts WHERE user_id = ? AND post_id = ?',
            [user_id, post_id]
        )
        commit_db()
        return True

    @staticmethod
    def get_saved_posts(user_id):
        """Получить сохранённые посты пользователя"""
        return query_db(
            '''SELECT posts.*, users.username, saved_posts.saved_at
               FROM posts 
               JOIN saved_posts ON posts.id = saved_posts.post_id
               JOIN users ON posts.author_id = users.id 
               WHERE saved_posts.user_id = ? 
               ORDER BY saved_posts.saved_at DESC''',
            [user_id]
        )


# Класс Comment
class Comment:
    """Модель комментария к посту"""

    @staticmethod
    def get_by_id(comment_id):
        """Получить комментарий по ID"""
        return query_db(
            '''SELECT comments.*, users.username 
               FROM comments 
               JOIN users ON comments.author_id = users.id 
               WHERE comments.id = ?''',
            [comment_id], one=True
        )

    @staticmethod
    def create(content, post_id, author_id):
        """Создать новый комментарий"""
        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            'INSERT INTO comments (content, post_id, author_id, created_at) VALUES (?, ?, ?, ?)',
            [content, post_id, author_id, now]
        )
        commit_db()

        # Получить ID последнего добавленного комментария
        comment_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        return Comment.get_by_id(comment_id)

    @staticmethod
    def update(comment_id, content):
        """Обновить комментарий"""
        db = get_db()
        db.execute(
            'UPDATE comments SET content = ? WHERE id = ?',
            [content, comment_id]
        )
        commit_db()
        return Comment.get_by_id(comment_id)

    @staticmethod
    def delete(comment_id):
        """Удалить комментарий"""
        db = get_db()
        db.execute('DELETE FROM comments WHERE id = ?', [comment_id])
        commit_db()
        return True

    @staticmethod
    def get_by_author(author_id):
        """Получить комментарии определенного автора"""
        return query_db(
            '''SELECT comments.*, users.username, posts.title as post_title
               FROM comments 
               JOIN users ON comments.author_id = users.id 
               JOIN posts ON comments.post_id = posts.id
               WHERE comments.author_id = ? 
               ORDER BY comments.created_at DESC''',
            [author_id]
        )

    @staticmethod
    def can_user_delete_comment(comment_id, user_id):
        """Check if user can delete comment (owner, post owner, or admin)"""
        # Admin can delete any comment
        if User.is_admin(user_id):
            return True

        comment = Comment.get_by_id(comment_id)
        if not comment:
            return False

        # Author of comment can delete it
        if comment['author_id'] == user_id:
            return True

        # Author of post can delete comments on their post
        post = Post.get_by_id(comment['post_id'])
        if post and post['author_id'] == user_id:
            return True

        return False

    @staticmethod
    def can_user_edit_comment(comment_id, user_id):
        """Check if user can edit comment (owner or admin)"""
        # Admin can edit any comment
        if User.is_admin(user_id):
            return True

        comment = Comment.get_by_id(comment_id)
        if not comment:
            return False

        # Only the author can edit their comment (or admin)
        return comment['author_id'] == user_id