from datetime import datetime, timezone

from backend.models.base import get_db, query_db, commit_db


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
        now = datetime.now(timezone.utc).isoformat()
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