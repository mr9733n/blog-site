# backend/routes/posts.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.models import Post, Comment, SavedPost

posts_bp = Blueprint('posts', __name__)

# Маршрут для получения всех постов
@posts_bp.route('/posts', methods=['GET'])
def get_posts():
    # Опциональные параметры для пагинации
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)

    posts = Post.get_all(limit=limit, offset=offset)
    return jsonify([dict(post) for post in posts])

# Маршрут для получения конкретного поста
@posts_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    return jsonify(dict(post))

# Маршрут для создания поста
@posts_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    current_user_id = get_jwt_identity()
    # Convert string ID back to integer
    current_user_id = int(current_user_id)
    data = request.get_json()

    try:
        post = Post.create(data['title'], data['content'], current_user_id)
        return jsonify({"msg": "Пост успешно создан", "post_id": post['id']}), 201
    except Exception as e:
        current_app.logger.error(f"Ошибка создания поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при создании поста"}), 500

# Маршрут для обновления поста
@posts_bp.route('/posts/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)
    data = request.get_json()

    current_app.logger.debug(f"Запрос на редактирование поста {post_id} от пользователя {user_id}")

    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        current_app.logger.error(f"Пост {post_id} не найден")
        return jsonify({"msg": "Пост не найден"}), 404

    # Проверка прав на редактирование
    if not Post.can_user_edit_post(post_id, user_id):
        current_app.logger.error(f"Пользователь {user_id} не имеет прав для редактирования поста {post_id}")
        return jsonify({"msg": "Нет прав для редактирования"}), 403

    try:
        # Валидация данных
        if not data.get('title', '').strip():
            return jsonify({"msg": "Заголовок не может быть пустым"}), 400

        if not data.get('content', '').strip():
            return jsonify({"msg": "Содержание поста не может быть пустым"}), 400

        Post.update(post_id, data['title'], data['content'])
        current_app.logger.info(f"Пост {post_id} успешно обновлен пользователем {user_id}")
        return jsonify({"msg": "Пост успешно обновлен"})
    except Exception as e:
        current_app.logger.error(f"Ошибка обновления поста {post_id}: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при обновлении поста"}), 500

# Маршрут для удаления поста
@posts_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    current_user_id = get_jwt_identity()
    # Convert string ID back to integer
    current_user_id = int(current_user_id)

    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    # Проверка прав на удаление
    if not Post.can_user_edit_post(post_id, current_user_id):
        return jsonify({"msg": "Нет прав для удаления"}), 403

    try:
        Post.delete(post_id)
        return jsonify({"msg": "Пост успешно удален"})
    except Exception as e:
        current_app.logger.error(f"Ошибка удаления поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении поста"}), 500

# Маршрут для получения постов конкретного пользователя
@posts_bp.route('/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    try:
        posts = Post.get_by_author(user_id)
        return jsonify([dict(post) for post in posts])
    except Exception as e:
        current_app.logger.error(f"Ошибка получения постов пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении постов"}), 500

# Маршруты для комментариев
@posts_bp.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    comments = Post.get_post_comments(post_id)
    return jsonify([dict(comment) for comment in comments])

@posts_bp.route('/posts/<int:post_id>/comments', methods=['POST'])
@jwt_required()
def create_comment(post_id):
    current_user_id = get_jwt_identity()
    # Convert string ID back to integer
    current_user_id = int(current_user_id)
    data = request.get_json()

    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    if not data.get('content', '').strip():
        return jsonify({"msg": "Содержание комментария не может быть пустым"}), 400

    try:
        comment = Comment.create(data['content'], post_id, current_user_id)
        return jsonify({"msg": "Комментарий успешно добавлен", "comment": dict(comment)}), 201
    except Exception as e:
        current_app.logger.error(f"Ошибка создания комментария: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при создании комментария"}), 500

# Маршруты для обновления и удаления комментариев
@posts_bp.route('/comments/<int:comment_id>', methods=['PUT'])
@jwt_required()
def update_comment(comment_id):
    current_user_id = get_jwt_identity()
    # Convert string ID back to integer
    current_user_id = int(current_user_id)
    data = request.get_json()

    # Проверка существования комментария
    comment = Comment.get_by_id(comment_id)
    if not comment:
        return jsonify({"msg": "Комментарий не найден"}), 404

    # Проверка прав на редактирование
    if not Comment.can_user_edit_comment(comment_id, current_user_id):
        return jsonify({"msg": "Нет прав для редактирования комментария"}), 403

    if not data.get('content', '').strip():
        return jsonify({"msg": "Содержание комментария не может быть пустым"}), 400

    try:
        updated_comment = Comment.update(comment_id, data['content'])
        return jsonify({"msg": "Комментарий успешно обновлен", "comment": dict(updated_comment)})
    except Exception as e:
        current_app.logger.error(f"Ошибка обновления комментария: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при обновлении комментария"}), 500

@posts_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    current_app.logger.debug(f"Запрос на удаление комментария {comment_id} от пользователя {user_id}")

    # Проверка существования комментария
    comment = Comment.get_by_id(comment_id)
    if not comment:
        current_app.logger.error(f"Комментарий {comment_id} не найден")
        return jsonify({"msg": "Комментарий не найден"}), 404

    # Проверка прав на удаление
    if not Comment.can_user_delete_comment(comment_id, user_id):
        current_app.logger.error(f"Пользователь {user_id} не имеет прав для удаления комментария {comment_id}")
        return jsonify({"msg": "Нет прав для удаления комментария"}), 403

    try:
        Comment.delete(comment_id)
        current_app.logger.info(f"Комментарий {comment_id} успешно удален пользователем {user_id}")
        return jsonify({"msg": "Комментарий успешно удален"})
    except Exception as e:
        current_app.logger.error(f"Ошибка удаления комментария {comment_id}: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении комментария"}), 500

# Маршруты для сохраненных постов
@posts_bp.route('/posts/<int:post_id>/save', methods=['POST'])
@jwt_required()
def save_post(post_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    try:
        result = SavedPost.save_post(user_id, post_id)

        if not result:
            return jsonify({"msg": "Пост уже сохранен"}), 200

        current_app.logger.info(f"Пользователь {user_id} сохранил пост {post_id}")
        return jsonify({"msg": "Пост добавлен в сохранённые"}), 200
    except Exception as e:
        current_app.logger.error(f"Ошибка сохранения поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при сохранении поста"}), 500

@posts_bp.route('/posts/<int:post_id>/unsave', methods=['POST'])
@jwt_required()
def unsave_post(post_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        result = SavedPost.unsave_post(user_id, post_id)

        if not result:
            return jsonify({"msg": "Пост не найден в сохранённых"}), 404

        current_app.logger.info(f"Пользователь {user_id} удалил пост {post_id} из сохранённых")
        return jsonify({"msg": "Пост удален из сохранённых"}), 200
    except Exception as e:
        current_app.logger.error(f"Ошибка удаления из сохранённых: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении из сохранённых"}), 500

@posts_bp.route('/saved/posts', methods=['GET'])
@jwt_required()
def get_saved_posts():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        saved_posts = SavedPost.get_saved_posts(user_id)
        return jsonify([dict(post) for post in saved_posts])
    except Exception as e:
        current_app.logger.error(f"Ошибка получения сохранённых постов: {str(e)}")
        return jsonify([])

@posts_bp.route('/posts/<int:post_id>/is_saved', methods=['GET'])
@jwt_required()
def is_post_saved(post_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        is_saved = SavedPost.is_post_saved_by_user(user_id, post_id)
        return jsonify({"is_saved": is_saved})
    except Exception as e:
        current_app.logger.error(f"Ошибка проверки сохранения поста: {str(e)}")
        return jsonify({"is_saved": False, "error": str(e)}), 500