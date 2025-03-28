import os
import sqlite3
import logging
import datetime
import json

from functools import wraps
from io import BytesIO
from flask_cors import CORS
from dotenv import load_dotenv
from flask import Flask, request, jsonify, g, send_from_directory, send_file
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt

from config import get_config
from models import User, Post, Comment, SavedPost, Image, get_db

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

logging.debug(f"Server time: {datetime.datetime.now().isoformat()}")
logging.debug(f"JWT_SECRET_KEY: {app.config['JWT_SECRET_KEY']}")
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

upload_dir = os.path.join(app.static_folder, 'uploads')
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)


@app.before_request
def log_request_info():
    if 'Authorization' in request.headers:
        logger.debug(f"DEBUG: Auth header received: {request.headers['Authorization'][:20]}...")
    else:
        logger.warning("DEBUG: No Authorization header in request")
        logger.debug(f"DEBUG: Available headers: {list(request.headers.keys())}")


@app.before_request
def check_request_size():
    if request.method == 'POST' and request.path.startswith('/api/images/upload'):
        # Check content length
        content_length = request.headers.get('Content-Length', type=int)
        if content_length and content_length > Image.MAX_IMAGE_SIZE:
            return jsonify({
                "msg": f"Размер загружаемого файла превышает допустимый (максимум {Image.MAX_IMAGE_SIZE // 1024 // 1024}MB)"
            }), 413  # Request Entity Too Large


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
        logger.error(f"Ошибка регистрации: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при регистрации"}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    if not User.verify_password(data['username'], data['password']):
        return jsonify({"msg": "Неверные учетные данные"}), 401

    user = dict(User.get_by_username(data['username']))
    user_id_str = str(user['id'])

    # Проверка блокировки пользователя
    if User.is_user_blocked(user['id']):
        return jsonify({"msg": "Ваш аккаунт заблокирован администратором"}), 403

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
@jwt_required()  # Вместо jwt_required(refresh=True)
def refresh():
    # Получить claims из текущего токена
    current_token = get_jwt()

    # Проверить, что это refresh токен
    if current_token.get('token_type') != 'refresh':
        return jsonify({"msg": "Требуется refresh token"}), 401

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


@app.route('/api/settings/token-settings', methods=['PUT'])
@jwt_required()
def update_token_settings():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    data = request.get_json()
    token_lifetime = data.get('token_lifetime')
    refresh_token_lifetime = data.get('refresh_token_lifetime')

    # Валидация входных данных
    if not token_lifetime or not isinstance(token_lifetime, int) or token_lifetime < 300 or token_lifetime > 86400:
        return jsonify({"msg": "Недопустимое значение времени жизни токена. Должно быть от 5 минут до 24 часов."}), 400

    if not refresh_token_lifetime or not isinstance(refresh_token_lifetime, int) or refresh_token_lifetime < 86400 or refresh_token_lifetime > 2592000:
        return jsonify({"msg": "Недопустимое значение времени жизни refresh токена. Должно быть от 1 до 30 дней."}), 400

    # Обновление настроек в базе данных
    User.update_token_settings(user_id, token_lifetime, refresh_token_lifetime)

    # Создаем новые токены с обновленными настройками
    access_token = create_access_token(
        identity=current_user_id,
        expires_delta=datetime.timedelta(seconds=token_lifetime)
    )

    refresh_token = create_refresh_token(
        identity=current_user_id,
        expires_delta=datetime.timedelta(seconds=refresh_token_lifetime)
    )

    return jsonify({
        "msg": "Настройки успешно обновлены",
        "token_lifetime": token_lifetime,
        "refresh_token_lifetime": refresh_token_lifetime,
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200

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
    user_id = int(current_user_id)
    data = request.get_json()

    logger.debug(f"Запрос на редактирование поста {post_id} от пользователя {user_id}")

    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        logger.error(f"Пост {post_id} не найден")
        return jsonify({"msg": "Пост не найден"}), 404

    # Проверка прав на редактирование (now uses can_user_edit_post which includes admin check)
    if not Post.can_user_edit_post(post_id, user_id):
        logger.error(f"Пользователь {user_id} не имеет прав для редактирования поста {post_id}")
        return jsonify({"msg": "Нет прав для редактирования"}), 403

    try:
        # Валидация данных
        if not data.get('title', '').strip():
            return jsonify({"msg": "Заголовок не может быть пустым"}), 400

        if not data.get('content', '').strip():
            return jsonify({"msg": "Содержание поста не может быть пустым"}), 400

        Post.update(post_id, data['title'], data['content'])
        logger.info(f"Пост {post_id} успешно обновлен пользователем {user_id}")
        return jsonify({"msg": "Пост успешно обновлен"})
    except Exception as e:
        logger.error(f"Ошибка обновления поста {post_id}: {str(e)}")
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

    # Проверка прав на удаление (now uses can_user_edit_post which includes admin check)
    if not Post.can_user_edit_post(post_id, current_user_id):
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

    # Проверка прав на редактирование (use new can_user_edit_comment that includes admin check)
    if not Comment.can_user_edit_comment(comment_id, current_user_id):
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
    user_id = int(current_user_id)

    logger.debug(f"Запрос на удаление комментария {comment_id} от пользователя {user_id}")

    # Проверка существования комментария
    comment = Comment.get_by_id(comment_id)
    if not comment:
        logger.error(f"Комментарий {comment_id} не найден")
        return jsonify({"msg": "Комментарий не найден"}), 404

    # Проверка прав на удаление
    if not Comment.can_user_delete_comment(comment_id, user_id):
        logger.error(f"Пользователь {user_id} не имеет прав для удаления комментария {comment_id}")
        return jsonify({"msg": "Нет прав для удаления комментария"}), 403

    try:
        Comment.delete(comment_id)
        logger.info(f"Комментарий {comment_id} успешно удален пользователем {user_id}")
        return jsonify({"msg": "Комментарий успешно удален"})
    except Exception as e:
        logger.error(f"Ошибка удаления комментария {comment_id}: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении комментария"}), 500


# Добавить пост в сохранённые
@app.route('/api/posts/<int:post_id>/save', methods=['POST'])
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

        logger.info(f"Пользователь {user_id} сохранил пост {post_id}")
        return jsonify({"msg": "Пост добавлен в сохранённые"}), 200
    except Exception as e:
        logger.error(f"Ошибка сохранения поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при сохранении поста"}), 500


# Удалить пост из сохранённых
@app.route('/api/posts/<int:post_id>/unsave', methods=['POST'])
@jwt_required()
def unsave_post(post_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        result = SavedPost.unsave_post(user_id, post_id)

        if not result:
            return jsonify({"msg": "Пост не найден в сохранённых"}), 404

        logger.info(f"Пользователь {user_id} удалил пост {post_id} из сохранённых")
        return jsonify({"msg": "Пост удален из сохранённых"}), 200
    except Exception as e:
        logger.error(f"Ошибка удаления из сохранённых: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении из сохранённых"}), 500


# Получить сохранённые посты пользователя
@app.route('/api/saved/posts', methods=['GET'])
@jwt_required()
def get_saved_posts():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        saved_posts = SavedPost.get_saved_posts(user_id)
        return jsonify([dict(post) for post in saved_posts])
    except Exception as e:
        logger.error(f"Ошибка получения сохранённых постов: {str(e)}")
        return jsonify([])


# Проверить, сохранен ли пост пользователем
@app.route('/api/posts/<int:post_id>/is_saved', methods=['GET'])
@jwt_required()
def is_post_saved(post_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        is_saved = SavedPost.is_post_saved_by_user(user_id, post_id)
        return jsonify({"is_saved": is_saved})
    except Exception as e:
        logger.error(f"Ошибка проверки сохранения поста: {str(e)}")
        return jsonify({"is_saved": False, "error": str(e)}), 500


# Маршруты для работы с изображениями

# Загрузка изображения
@app.route('/api/images/upload', methods=['POST'])
@jwt_required()
def upload_image():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    # Проверка наличия файла в запросе
    if 'file' not in request.files:
        return jsonify({"msg": "Файл не найден в запросе"}), 400

    file = request.files['file']

    # Проверка, что файл выбран
    if file.filename == '':
        return jsonify({"msg": "Файл не выбран"}), 400

    # Получение ID поста, если указан
    post_id = request.form.get('post_id')
    if post_id:
        try:
            post_id = int(post_id)
            # Проверка существования поста и прав доступа
            post = Post.get_by_id(post_id)
            if not post:
                return jsonify({"msg": "Пост не найден"}), 404

            if post['author_id'] != user_id:
                return jsonify({"msg": "Нет прав для добавления изображения к этому посту"}), 403
        except ValueError:
            return jsonify({"msg": "Некорректный ID поста"}), 400
    else:
        post_id = None

    try:
        # Сохраняем изображение
        image = Image.save_file(file, user_id, post_id)

        # Формируем ответ с информацией о загруженном изображении
        # Remove the image_data field from the response to avoid serialization issues
        image_data = dict(image)
        if 'image_data' in image_data:
            del image_data['image_data']  # Remove binary data from the response

        return jsonify({
            "msg": "Изображение успешно загружено",
            "image": image_data
        }), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при загрузке изображения"}), 500


# Получить изображение по ID
@app.route('/api/images/<int:image_id>', methods=['GET'])
def get_image(image_id):
    try:
        image = Image.get_by_id(image_id)
        if not image:
            return jsonify({"msg": "Изображение не найдено"}), 404

        return jsonify(dict(image))
    except Exception as e:
        logger.error(f"Ошибка получения информации об изображении: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении информации об изображении"}), 500


# Получить изображения поста
@app.route('/api/posts/<int:post_id>/images', methods=['GET'])
def get_post_images(post_id):
    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    try:
        images = Image.get_by_post(post_id)
        return jsonify([dict(image) for image in images])
    except Exception as e:
        logger.error(f"Ошибка получения изображений поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении изображений"}), 500


# Получить изображения пользователя
@app.route('/api/users/<int:user_id>/images', methods=['GET'])
def get_user_images(user_id):
    # Опциональный параметр для ограничения количества
    limit = request.args.get('limit', type=int)

    try:
        images = Image.get_by_author(user_id, limit)

        # Преобразуем объекты Row в словари и удаляем бинарные данные
        result = []
        for image in images:
            image_dict = dict(image)
            if 'image_data' in image_dict:
                del image_dict['image_data']  # Удаляем бинарные данные
            result.append(image_dict)

        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка получения изображений пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении изображений"}), 500


# Удалить изображение
@app.route('/api/images/<int:image_id>', methods=['DELETE'])
@jwt_required()
def delete_image(image_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        # Проверка существования изображения
        image = Image.get_by_id(image_id)
        if not image:
            return jsonify({"msg": "Изображение не найдено"}), 404

        # Проверка прав на удаление (use can_user_manage_image to include admin)
        if not Image.can_user_manage_image(image_id, user_id):
            return jsonify({"msg": "Нет прав для удаления изображения"}), 403

        # Удаляем изображение
        result = Image.delete(image_id)
        if not result:
            return jsonify({"msg": "Не удалось удалить изображение"}), 500

        return jsonify({"msg": "Изображение успешно удалено"})
    except Exception as e:
        logger.error(f"Ошибка удаления изображения: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении изображения"}), 500


# Привязать изображение к посту
@app.route('/api/images/<int:image_id>/post/<int:post_id>', methods=['PUT'])
@jwt_required()
def attach_image_to_post(image_id, post_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        # Проверка существования изображения
        image = Image.get_by_id(image_id)
        if not image:
            return jsonify({"msg": "Изображение не найдено"}), 404

        # Проверка прав на изменение изображения (include admin check)
        if not Image.can_user_manage_image(image_id, user_id):
            return jsonify({"msg": "Нет прав для изменения изображения"}), 403

        # Проверка существования поста
        post = Post.get_by_id(post_id)
        if not post:
            return jsonify({"msg": "Пост не найден"}), 404

        # Проверка прав на редактирование поста (include admin check)
        if not Post.can_user_edit_post(post_id, user_id):
            return jsonify({"msg": "Нет прав для добавления изображения к этому посту"}), 403

        # Привязываем изображение к посту
        result = Image.update_post_id(image_id, post_id)
        if not result:
            return jsonify({"msg": "Не удалось привязать изображение к посту"}), 500

        return jsonify({"msg": "Изображение успешно привязано к посту"})
    except Exception as e:
        logger.error(f"Ошибка привязки изображения к посту: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при привязке изображения к посту"}), 500


# Отвязать изображение от поста
@app.route('/api/images/<int:image_id>/post', methods=['DELETE'])
@jwt_required()
def detach_image_from_post(image_id):
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)

    try:
        # Проверка существования изображения
        image = Image.get_by_id(image_id)
        if not image:
            return jsonify({"msg": "Изображение не найдено"}), 404

        # Проверка прав на изменение изображения (include admin check)
        if not Image.can_user_manage_image(image_id, user_id):
            return jsonify({"msg": "Нет прав для изменения изображения"}), 403

        # Отвязываем изображение от поста (устанавливаем post_id = NULL)
        result = Image.update_post_id(image_id, None)
        if not result:
            return jsonify({"msg": "Не удалось отвязать изображение от поста"}), 500

        return jsonify({"msg": "Изображение успешно отвязано от поста"})
    except Exception as e:
        logger.error(f"Ошибка отвязки изображения от поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при отвязке изображения от поста"}), 500


# Статический маршрут для доступа к загруженным изображениям
@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.static_folder, 'uploads'), filename)


@app.route('/api/images/data/<path:filename>')
def get_image_data(filename):
    try:
        # Get image data from database
        image_data = Image.get_image_data(filename)

        if not image_data:
            return jsonify({"msg": "Изображение не найдено"}), 404

        # Send the binary data as a file
        return send_file(
            BytesIO(image_data['data']),
            mimetype=image_data['filetype'],
            as_attachment=False,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Ошибка получения изображения: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении изображения"}), 500


# Проверка прав администратора для запросов
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id)

        # Проверка административных прав
        if not User.is_admin(user_id):
            return jsonify({"msg": "Требуются права администратора"}), 403

        return fn(*args, **kwargs)

    return wrapper


# Маршрут для получения списка пользователей (только для админа)
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    try:
        users = User.get_all_users_with_status()
        # Удаляем хеши паролей из ответа
        for user in users:
            user.pop('password', None)
        return jsonify(users)
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении списка пользователей"}), 500


# Маршрут для получения подробной информации о пользователе (только для админа)
@app.route('/api/admin/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(user_id):
    try:
        user = User.get_user_with_status(user_id)
        if not user:
            return jsonify({"msg": "Пользователь не найден"}), 404

        # Удаляем хеш пароля из ответа
        user.pop('password', None)

        return jsonify(user)
    except Exception as e:
        logger.error(f"Ошибка получения данных пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении данных пользователя"}), 500


# Маршрут для блокировки/разблокировки пользователя (только для админа)
@app.route('/api/admin/users/<int:user_id>/block', methods=['POST'])
@admin_required
def toggle_user_block(user_id):
    try:
        data = request.get_json()
        blocked = data.get('blocked', False)

        result = User.toggle_user_block(user_id, blocked)

        if blocked:
            return jsonify({"msg": "Пользователь успешно заблокирован"})
        else:
            return jsonify({"msg": "Пользователь успешно разблокирован"})
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка изменения блокировки пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при изменении блокировки пользователя"}), 500


# Маршрут для обновления данных пользователя (только для админа)
@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Обновляем данные пользователя
        result = User.update_user(user_id, username, email, password)

        if result:
            return jsonify({"msg": "Данные пользователя успешно обновлены"})
        else:
            return jsonify({"msg": "Нет данных для обновления"}), 400
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка обновления данных пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при обновлении данных пользователя"}), 500


# Проверка блокировки пользователя при аутентификации
@app.before_request
def check_if_user_blocked():
    # Проверяем только запросы API, которые не являются авторизацией
    if request.path.startswith('/api/') and request.path != '/api/login' and request.path != '/api/register':
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                token = auth_header.split(' ')[1]

                # Декодируем токен без проверки сигнатуры
                from jwt import decode
                payload = decode(token, options={"verify_signature": False})

                user_id = payload.get('sub')

                # Проверяем, заблокирован ли пользователь
                if user_id and User.is_user_blocked(user_id):
                    return jsonify({"msg": "Ваш аккаунт заблокирован администратором"}), 403
            except Exception as e:
                # Пропускаем ошибки декодирования токена
                pass

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])