// src/utils/formatUtils.js
/**
 * Форматирует дату в локализованный строковый формат
 * @param {string|Date} dateString - Дата в формате строки или объект Date
 * @param {Object} options - Опции форматирования
 * @returns {string} - Форматированная строка даты
 */
export function formatDate(dateString, options = {}) {
  if (!dateString) return 'N/A';

  const date = dateString instanceof Date ? dateString : new Date(dateString);

  // Проверка валидности даты
  if (isNaN(date.getTime())) return 'Invalid date';

  // Настройки по умолчанию
  const defaultOptions = {
    locale: 'ru',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: undefined,
    minute: undefined
  };

  // Объединяем настройки по умолчанию с пользовательскими
  const formatOptions = { ...defaultOptions, ...options };

  // Извлекаем locale и удаляем его из объекта options, так как он не является частью DateTimeFormatOptions
  const { locale, ...dateTimeOptions } = formatOptions;

  try {
    return new Intl.DateTimeFormat(locale, dateTimeOptions).format(date);
  } catch (error) {
    console.error('Error formatting date:', error);
    return dateString.toString();
  }
}

/**
 * Форматирует размер файла в человекочитаемый формат
 * @param {number} bytes - Размер в байтах
 * @param {number} decimals - Количество знаков после запятой
 * @returns {string} - Форматированная строка размера
 */
export function formatFileSize(bytes, decimals = 1) {
  if (bytes === 0) return '0 Bytes';
  if (!bytes || isNaN(bytes)) return 'N/A';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

/**
 * Форматирует таймштамп в формат "прошло времени" (например, "5 минут назад")
 * @param {string|Date} timestamp - Дата в формате строки или объект Date
 * @param {string} locale - Локаль для форматирования (по умолчанию 'ru')
 * @returns {string} - Относительное время
 */
export function formatTimeAgo(timestamp, locale = 'ru') {
  if (!timestamp) return '';

  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  // Проверка валидности даты
  if (isNaN(date.getTime())) return 'Invalid date';

  // Словари для разных локалей
  const locales = {
    ru: {
      seconds: ['секунду', 'секунды', 'секунд'],
      minutes: ['минуту', 'минуты', 'минут'],
      hours: ['час', 'часа', 'часов'],
      days: ['день', 'дня', 'дней'],
      weeks: ['неделю', 'недели', 'недель'],
      months: ['месяц', 'месяца', 'месяцев'],
      years: ['год', 'года', 'лет'],
      ago: 'назад',
      justNow: 'только что',
      future: 'в будущем'
    },
    en: {
      seconds: ['second', 'seconds', 'seconds'],
      minutes: ['minute', 'minutes', 'minutes'],
      hours: ['hour', 'hours', 'hours'],
      days: ['day', 'days', 'days'],
      weeks: ['week', 'weeks', 'weeks'],
      months: ['month', 'months', 'months'],
      years: ['year', 'years', 'years'],
      ago: 'ago',
      justNow: 'just now',
      future: 'in the future'
    }
  };

  // Использовать словарь для указанной локали или для 'en' по умолчанию
  const dict = locales[locale] || locales.en;

  // Функция для выбора правильной формы слова (для русского языка)
  const pluralize = (number, words) => {
    if (locale === 'ru') {
      const cases = [2, 0, 1, 1, 1, 2];
      const index = (number % 100 > 4 && number % 100 < 20) ? 2 : cases[Math.min(number % 10, 5)];
      return `${number} ${words[index]}`;
    } else {
      return `${number} ${words[number === 1 ? 0 : 1]}`;
    }
  };

  // Будущее время
  if (seconds < 0) {
    return dict.future;
  }

  // Выбор временного периода
  let interval = Math.floor(seconds / 31536000); // Годы
  if (interval >= 1) {
    return `${pluralize(interval, dict.years)} ${dict.ago}`;
  }

  interval = Math.floor(seconds / 2592000); // Месяцы
  if (interval >= 1) {
    return `${pluralize(interval, dict.months)} ${dict.ago}`;
  }

  interval = Math.floor(seconds / 604800); // Недели
  if (interval >= 1) {
    return `${pluralize(interval, dict.weeks)} ${dict.ago}`;
  }

  interval = Math.floor(seconds / 86400); // Дни
  if (interval >= 1) {
    return `${pluralize(interval, dict.days)} ${dict.ago}`;
  }

  interval = Math.floor(seconds / 3600); // Часы
  if (interval >= 1) {
    return `${pluralize(interval, dict.hours)} ${dict.ago}`;
  }

  interval = Math.floor(seconds / 60); // Минуты
  if (interval >= 1) {
    return `${pluralize(interval, dict.minutes)} ${dict.ago}`;
  }

  // Меньше минуты
  if (seconds < 10) {
    return dict.justNow;
  }

  return `${pluralize(Math.floor(seconds), dict.seconds)} ${dict.ago}`;
}

/**
 * Маскирует электронную почту для отображения
 * (Перемещено из userStore.js для централизации утилит форматирования)
 * @param {string} email - Email для маскировки
 * @returns {string} - Маскированный email
 */
export function maskEmail(email) {
  if (!email) return '';

  try {
    const [username, domain] = email.split('@');

    // Обработка случаев с некорректным форматом email
    if (!domain) return email;

    let maskedUsername;
    if (username.length <= 4) {
      maskedUsername = username.charAt(0) + '*'.repeat(username.length - 2) + username.charAt(username.length - 1);
    } else {
      maskedUsername = username.slice(0, 2) + '*'.repeat(username.length - 4) + username.slice(-2);
    }

    let maskedDomain;
    if (domain.length <= 4) {
      maskedDomain = domain.charAt(0) + '*'.repeat(domain.length - 2) + domain.charAt(domain.length - 1);
    } else {
      maskedDomain = domain.slice(0, 2) + '*'.repeat(domain.length - 4) + domain.slice(-2);
    }

    return `${maskedUsername}@${maskedDomain}`;
  } catch (error) {
    console.error('Error masking email:', error);
    return email; // Возвращаем исходный email в случае ошибки
  }
}