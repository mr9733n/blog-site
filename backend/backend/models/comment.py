from datetime import datetime

from backend.models.user import User
from backend.models.post import Post
from backend.models.base import get_db, query_db, commit_db


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