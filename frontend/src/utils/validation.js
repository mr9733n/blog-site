// src/utils/validation.js
// Утилиты для валидации пользовательского ввода

/**
 * Валидирует имя пользователя
 * @param {string} username - Имя пользователя для проверки
 * @returns {Object} - Результат валидации { valid: boolean, error: string }
 */
export function validateUsername(username) {
  if (!username) {
    return { valid: false, error: 'Имя пользователя обязательно' };
  }

  if (username.length < 3) {
    return { valid: false, error: 'Имя пользователя должно содержать минимум 3 символа' };
  }

  if (username.length > 30) {
    return { valid: false, error: 'Имя пользователя не должно превышать 30 символов' };
  }

  // Проверка на запрещенные символы
  const forbiddenChars = /['";<>\\]/;
  if (forbiddenChars.test(username)) {
    return {
      valid: false,
      error: 'Имя пользователя содержит недопустимые символы (\'";\\<>)'
    };
  }

  // Разрешены только буквы, цифры, подчеркивания и дефисы
  const validFormat = /^[a-zA-Zа-яА-Я0-9_\-\.]+$/;
  if (!validFormat.test(username)) {
    return {
      valid: false,
      error: 'Имя пользователя может содержать только буквы, цифры, подчеркивания и дефисы'
    };
  }

  return { valid: true, error: null };
}

/**
 * Валидирует пароль
 * @param {string} password - Пароль для проверки
 * @returns {Object} - Результат валидации { valid: boolean, error: string, strength: number }
 */
export function validatePassword(password) {
  if (!password) {
    return { valid: false, error: 'Пароль обязателен', strength: 0 };
  }

  if (password.length < 6) {
    return {
      valid: false,
      error: 'Пароль должен содержать минимум 6 символов',
      strength: 1
    };
  }

  // Проверка на запрещенные символы
  const forbiddenChars = /['";<>]/;
  if (forbiddenChars.test(password)) {
    return {
      valid: false,
      error: 'Пароль содержит недопустимые символы',
      strength: 0
    };
  }

  // Оценка силы пароля
  let strength = 0;

  // Имеет буквы в нижнем регистре
  if (/[a-z]/.test(password)) strength++;

  // Имеет буквы в верхнем регистре
  if (/[A-Z]/.test(password)) strength++;

  // Имеет цифры
  if (/[0-9]/.test(password)) strength++;

  // Имеет специальные символы
  if (/[^a-zA-Z0-9]/.test(password)) strength++;

  // Длина более 8 символов
  if (password.length >= 8) strength++;

  // Если пароль слишком слабый но проходит минимальные требования
  if (strength < 3) {
    return {
      valid: true,
      warning: 'Рекомендуется использовать более сложный пароль',
      strength
    };
  }

  return { valid: true, error: null, strength };
}

/**
 * Валидирует формат email
 * @param {string} email - Email для проверки
 * @returns {Object} - Результат валидации { valid: boolean, error: string }
 */
export function validateEmail(email) {
  if (!email) {
    return { valid: false, error: 'Email обязателен' };
  }

  // RFC 5322 совместимое регулярное выражение для проверки email
  const emailRegex = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

  if (!emailRegex.test(email)) {
    return { valid: false, error: 'Некорректный формат email' };
  }

  return { valid: true, error: null };
}

/**
 * Валидирует заголовок поста
 * @param {string} title - Заголовок для проверки
 * @returns {Object} - Результат валидации { valid: boolean, error: string }
 */
export function validatePostTitle(title) {
  if (!title || !title.trim()) {
    return { valid: false, error: 'Заголовок не может быть пустым' };
  }

  if (title.length < 3) {
    return { valid: false, error: 'Заголовок должен содержать минимум 3 символа' };
  }

  if (title.length > 100) {
    return { valid: false, error: 'Заголовок не должен превышать 100 символов' };
  }

  return { valid: true, error: null };
}

/**
 * Валидирует содержимое поста
 * @param {string} content - Содержимое для проверки
 * @returns {Object} - Результат валидации { valid: boolean, error: string }
 */
export function validatePostContent(content) {
  if (!content || !content.trim()) {
    return { valid: false, error: 'Содержимое поста не может быть пустым' };
  }

  if (content.length < 10) {
    return { valid: false, error: 'Содержимое поста должно содержать минимум 10 символов' };
  }

  // Проверка на чрезмерно большое содержимое
  if (content.length > 50000) {
    return {
      valid: false,
      error: 'Содержимое поста не должно превышать 50,000 символов'
    };
  }

  return { valid: true, error: null };
}

/**
 * Валидирует комментарий
 * @param {string} comment - Комментарий для проверки
 * @returns {Object} - Результат валидации { valid: boolean, error: string }
 */
export function validateComment(comment) {
  if (!comment || !comment.trim()) {
    return { valid: false, error: 'Комментарий не может быть пустым' };
  }

  if (comment.length < 2) {
    return { valid: false, error: 'Комментарий должен содержать минимум 2 символа' };
  }

  if (comment.length > 1000) {
    return {
      valid: false,
      error: 'Комментарий не должен превышать 1000 символов'
    };
  }

  return { valid: true, error: null };
}

/**
 * Валидирует загружаемый файл изображения
 * @param {File} file - Файл для проверки
 * @param {number} maxSize - Максимальный размер в байтах (по умолчанию 5MB)
 * @returns {Object} - Результат валидации { valid: boolean, error: string }
 */
export function validateImageFile(file, maxSize = 5 * 1024 * 1024) {
  if (!file) {
    return { valid: false, error: 'Файл не выбран' };
  }

  // Проверка типа файла
  if (!file.type.startsWith('image/')) {
    return { valid: false, error: 'Выбранный файл не является изображением' };
  }

  // Проверка поддерживаемых форматов
  const supportedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
  if (!supportedTypes.includes(file.type)) {
    return {
      valid: false,
      error: 'Неподдерживаемый формат изображения. Поддерживаются: JPG, PNG, GIF, WEBP'
    };
  }

  // Проверка размера файла
  if (file.size > maxSize) {
    const maxSizeMB = maxSize / (1024 * 1024);
    return {
      valid: false,
      error: `Размер файла не должен превышать ${maxSizeMB} MB`
    };
  }

  return { valid: true, error: null };
}

/**
 * Обобщенная функция валидации форм
 * @param {Object} fields - Объект с полями формы и их типами
 * @returns {Object} - Результат валидации { valid: boolean, errors: Object }
 */
export function validateForm(fields) {
  const errors = {};
  let isValid = true;

  for (const [fieldName, { value, type }] of Object.entries(fields)) {
    let validationResult;

    switch (type) {
      case 'username':
        validationResult = validateUsername(value);
        break;
      case 'password':
        validationResult = validatePassword(value);
        break;
      case 'email':
        validationResult = validateEmail(value);
        break;
      case 'postTitle':
        validationResult = validatePostTitle(value);
        break;
      case 'postContent':
        validationResult = validatePostContent(value);
        break;
      case 'comment':
        validationResult = validateComment(value);
        break;
      case 'imageFile':
        validationResult = validateImageFile(value);
        break;
      default:
        validationResult = { valid: true, error: null };
    }

    if (!validationResult.valid) {
      errors[fieldName] = validationResult.error;
      isValid = false;
    } else if (validationResult.warning) {
      errors[fieldName] = { warning: validationResult.warning };
    }
  }

  return { valid: isValid, errors };
}