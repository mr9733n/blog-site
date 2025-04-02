from datetime import datetime

from backend.models.user import User
from backend.models.base import get_db, query_db, commit_db


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