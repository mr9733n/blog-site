import os
import sqlite3
import logging
import datetime

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

from config import get_config
from models import User, Post, Comment
from dotenv import load_dotenv

load_dotenv()

def configure_logging(app):
    log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO

    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get a logger for your app
    logger = logging.getLogger('blog-app')
    logger.setLevel(log_level)

    # Add it to app for easy access
    app.logger = logger

    return logger

app = Flask(__name__)
app.config.from_object(get_config())
logger = configure_logging(app)

logging.debug("Server time:", datetime.datetime.now().isoformat())
logging.debug("JWT_SECRET_KEY:", app.config['JWT_SECRET_KEY'])
# Настройка CORS
CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})

# Настройка JWT
jwt = JWTManager(app)


# Закрытие соединения с БД после обработки запроса
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Инициализация базы данных
def init_db():
    with app.app_context():
        db = g._database = sqlite3.connect(app.config['DATABASE_PATH'])
        with app.open_resource('schema.sql', mode='r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()


# Создание таблиц если их нет
def setup():
    with app.app_context():
        if not os.path.exists(app.config['DATABASE_PATH']):
            init_db()


# Регистрация функции инициализации БД
with app.app_context():
    # Запускаем функцию setup() при старте приложения
    setup()


@app.before_request
def log_request_info():
    if 'Authorization' in request.headers:
        logger.debug(f"DEBUG: Auth header received: {request.headers['Authorization'][:20]}...")
    else:
        logger.warning("DEBUG: No Authorization header in request")
        logger.debug(f"DEBUG: Available headers: {list(request.headers.keys())}")


# Маршруты для авторизации
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()

    try:
        User.create(data['username'], data['email'], data['password'])
        return jsonify({"msg": "Пользователь успешно зарегистрирован"}), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Ошибка регистрации: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при регистрации"}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    if not User.verify_password(data['username'], data['password']):
        return jsonify({"msg": "Неверные учетные данные"}), 401

    user = dict(User.get_by_username(data['username']))
    user_id_str = str(user['id'])

    # Get user's token lifetime setting
    token_lifetime = User.get_token_lifetime(user['id'])

    # Create tokens
    from flask_jwt_extended import create_access_token, create_refresh_token
    access_token = create_access_token(
        identity=user_id_str,
        expires_delta=datetime.timedelta(seconds=token_lifetime)
    )
    refresh_token = create_refresh_token(identity=user_id_str)

    return jsonify(
        access_token=access_token,
        refresh_token=refresh_token,
        token_lifetime=token_lifetime
    ), 200


@app.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    # Convert to int for database lookup
    user_id = int(current_user_id)

    # Get user's token lifetime setting
    token_lifetime = User.get_token_lifetime(user_id)

    # Create new access token
    access_token = create_access_token(
        identity=current_user_id,
        expires_delta=datetime.timedelta(seconds=token_lifetime)
    )

    return jsonify(access_token=access_token, token_lifetime=token_lifetime), 200


@app.route('/api/settings/token-lifetime', methods=['PUT'])
@jwt_required()
def update_token_lifetime():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    data = request.get_json()
    lifetime = data.get('token_lifetime')
    logger.debug(f"DEBUG: token-lifetime: {lifetime}")

    # Validate input
    if not lifetime or not isinstance(lifetime, int) or lifetime < 300 or lifetime > 86400:
        return jsonify({"msg": "Недопустимое значение времени жизни токена. Должно быть от 5 минут до 24 часов."}), 400

    # Update setting
    User.update_token_lifetime(user_id, lifetime)

    return jsonify({"msg": "Настройки успешно обновлены", "token_lifetime": lifetime}), 200


# Add this after initializing jwt
@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    logger.error(f"DEBUG: Invalid token error: {error_string}")
    return jsonify({"msg": f"Invalid token: {error_string}"}), 422


@jwt.unauthorized_loader
def unauthorized_callback(error_string):
    logger.error(f"DEBUG: Unauthorized error: {error_string}")
    return jsonify({"msg": f"Unauthorized: {error_string}"}), 401

# Маршруты для блог-постов
@app.route('/api/posts', methods=['GET'])
def get_posts():
    # Опциональные параметры для пагинации
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)

    posts = Post.get_all(limit=limit, offset=offset)
    return jsonify([dict(post) for post in posts])


@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    return jsonify(dict(post))


@app.route('/api/posts', methods=['POST'])
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
        logger.error(f"Ошибка создания поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при создании поста"}), 500


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    # Проверка прав на редактирование
    if post['author_id'] != current_user_id:
        return jsonify({"msg": "Нет прав для редактирования"}), 403

    try:
        Post.update(post_id, data['title'], data['content'])
        return jsonify({"msg": "Пост успешно обновлен"})
    except Exception as e:
        logger.error(f"Ошибка обновления поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при обновлении поста"}), 500


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
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
    if post['author_id'] != current_user_id:
        return jsonify({"msg": "Нет прав для удаления"}), 403

    try:
        Post.delete(post_id)
        return jsonify({"msg": "Пост успешно удален"})
    except Exception as e:
        logger.error(f"Ошибка удаления поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении поста"}), 500


# Маршрут для получения постов конкретного пользователя
@app.route('/api/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    try:
        posts = Post.get_by_author(user_id)
        return jsonify([dict(post) for post in posts])
    except Exception as e:
        logger.error(f"Ошибка получения постов пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении постов"}), 500


# Маршрут для получения информации о текущем пользователе
@app.route('/api/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user_id = get_jwt_identity()
    # Convert string ID back to integer
    current_user_id = int(current_user_id)
    user = User.get_by_id(current_user_id)

    if not user:
        return jsonify({"msg": "Пользователь не найден"}), 404

    # Не возвращаем хеш пароля
    user_data = dict(user)
    user_data.pop('password', None)

    return jsonify(user_data)


# Маршруты для комментариев
@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    comments = Post.get_post_comments(post_id)
    return jsonify([dict(comment) for comment in comments])


@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
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
        logger.error(f"Ошибка создания комментария: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при создании комментария"}), 500


@app.route('/api/comments/<int:comment_id>', methods=['PUT'])
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
    if comment['author_id'] != current_user_id:
        return jsonify({"msg": "Нет прав для редактирования комментария"}), 403

    if not data.get('content', '').strip():
        return jsonify({"msg": "Содержание комментария не может быть пустым"}), 400

    try:
        updated_comment = Comment.update(comment_id, data['content'])
        return jsonify({"msg": "Комментарий успешно обновлен", "comment": dict(updated_comment)})
    except Exception as e:
        logger.error(f"Ошибка обновления комментария: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при обновлении комментария"}), 500


@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    current_user_id = get_jwt_identity()
    # Convert string ID back to integer
    current_user_id = int(current_user_id)

    # Проверка существования комментария
    comment = Comment.get_by_id(comment_id)
    if not comment:
        return jsonify({"msg": "Комментарий не найден"}), 404

    # Получаем пост для проверки, является ли пользователь автором поста
    post = Post.get_by_id(comment['post_id'])

    # Проверка прав на удаление (может удалить автор комментария или автор поста)
    if comment['author_id'] != current_user_id and post['author_id'] != current_user_id:
        return jsonify({"msg": "Нет прав для удаления комментария"}), 403

    try:
        Comment.delete(comment_id)
        return jsonify({"msg": "Комментарий успешно удален"})
    except Exception as e:
        logger.error(f"Ошибка удаления комментария: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении комментария"}), 500


if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])