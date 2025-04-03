# backend/routes/images.py
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from io import BytesIO

from backend.models import User, Image, Post

images_bp = Blueprint('images', __name__)

# Проверка размера загружаемого файла
@images_bp.before_request
def check_request_size():
    if request.method == 'POST' and request.path.endswith('/upload'):
        # Проверка наличия файла в запросе
        if 'file' not in request.files:
            return jsonify({"msg": "Файл не найден в запросе"}), 400

        file = request.files['file']

        # Проверка, что файл выбран
        if file.filename == '':
            return jsonify({"msg": "Файл не выбран"}), 400

        # Проверка типа файла перед чтением всего содержимого
        if not Image.allowed_file(file.filename):
            return jsonify({"msg": "Недопустимый формат файла"}), 400

        # Промежуточная проверка размера файла перед полной обработкой
        max_upload_size = current_app.config['MAX_UPLOAD_IMAGE_SIZE']

        # Используем seek для безопасного чтения размера файла
        file.seek(0, 2)  # Перемещаем указатель в конец файла
        file_size = file.tell()
        file.seek(0)  # Возвращаем указатель в начало

        # Предварительная проверка размера файла
        if file_size > max_upload_size:
            return jsonify({
                "msg": f"Размер загружаемого файла превышает допустимый (максимум {max_upload_size // 1024 // 1024}MB)"
            }), 413  # Request Entity Too Large

# Загрузка изображения
@images_bp.route('/images/upload', methods=['POST'])
@jwt_required()
def upload_image():
    current_app.logger.debug(f"Request Content-Type: {request.content_type}")
    current_app.logger.debug(f"Available files: {list(request.files.keys()) if request.files else 'None'}")
    current_app.logger.debug(f"Available form fields: {list(request.form.keys()) if request.form else 'None'}")

    # Проверка наличия файла в запросе
    if 'file' not in request.files:
        return jsonify({"msg": "Файл не найден в запросе"}), 400

    current_user_id = get_jwt_identity()
    # Convert string ID back to integer
    current_user_id = int(current_user_id)
    # Check User exists
    user = User.get_by_id(current_user_id)
    if not user:
        return jsonify({"msg": "Пользователь не найден"}), 403

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

            if post['author_id'] != current_user_id:
                return jsonify({"msg": "Нет прав для добавления изображения к этому посту"}), 403
        except ValueError:
            return jsonify({"msg": "Некорректный ID поста"}), 400
    else:
        post_id = None

    try:
        # Сохраняем изображение
        image = Image.save_file(file, current_user_id, post_id)

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
        current_app.logger.error(f"Ошибка загрузки изображения: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при загрузке изображения"}), 500

# Получить изображение по ID
@images_bp.route('/images/<int:image_id>', methods=['GET'])
def get_image(image_id):
    try:
        image = Image.get_by_id(image_id)
        if not image:
            return jsonify({"msg": "Изображение не найдено"}), 404

        return jsonify(dict(image))
    except Exception as e:
        current_app.logger.error(f"Ошибка получения информации об изображении: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении информации об изображении"}), 500

# Получить изображения поста
@images_bp.route('/posts/<int:post_id>/images', methods=['GET'])
def get_post_images(post_id):
    # Проверка существования поста
    post = Post.get_by_id(post_id)
    if not post:
        return jsonify({"msg": "Пост не найден"}), 404

    try:
        images = Image.get_by_post(post_id)
        return jsonify([dict(image) for image in images])
    except Exception as e:
        current_app.logger.error(f"Ошибка получения изображений поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении изображений"}), 500

# Получить изображения пользователя
@images_bp.route('/users/<int:user_id>/images', methods=['GET'])
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
        current_app.logger.error(f"Ошибка получения изображений пользователя: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении изображений"}), 500

# Удалить изображение
@images_bp.route('/images/<int:image_id>', methods=['DELETE'])
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
        current_app.logger.error(f"Ошибка удаления изображения: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при удалении изображения"}), 500

# Привязать изображение к посту
@images_bp.route('/images/<int:image_id>/post/<int:post_id>', methods=['PUT'])
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
        current_app.logger.error(f"Ошибка привязки изображения к посту: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при привязке изображения к посту"}), 500

# Отвязать изображение от поста
@images_bp.route('/images/<int:image_id>/post', methods=['DELETE'])
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
        current_app.logger.error(f"Ошибка отвязки изображения от поста: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при отвязке изображения от поста"}), 500

# Получить данные изображения по имени файла
@images_bp.route('/images/data/<path:filename>')
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
        current_app.logger.error(f"Ошибка получения изображения: {str(e)}")
        return jsonify({"msg": "Произошла ошибка при получении изображения"}), 500