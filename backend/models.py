import sqlite3
from flask import g
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


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

    @staticmethod
    def can_user_edit_post(post_id, user_id):
        """Проверить, может ли пользователь редактировать пост"""
        post = Post.get_by_id(post_id)
        if not post:
            return False
        return post['author_id'] == user_id

# Добавим класс SavedPost в models.py

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


# Дополненный класс Comment в models.py

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
        """Проверить, может ли пользователь удалить комментарий
        (если он автор комментария или автор поста)"""
        comment = Comment.get_by_id(comment_id)
        if not comment:
            return False

        # Если пользователь - автор комментария
        if comment['author_id'] == user_id:
            return True

        # Если пользователь - автор поста
        post = Post.get_by_id(comment['post_id'])
        if post and post['author_id'] == user_id:
            return True

        return False