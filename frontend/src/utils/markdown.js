// src/utils/markdown.js
// Улучшенный рендеринг markdown с лучшей защитой от XSS

/**
 * Экранирует HTML-теги для предотвращения XSS
 * @param {string} unsafe - Небезопасный HTML-текст
 * @returns {string} - Экранированный HTML
 */
function escapeHtml(unsafe) {
  if (!unsafe) return '';

  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Проверяет ссылку на безопасность
 * @param {string} url - URL для проверки
 * @returns {boolean} - true если URL безопасен
 */
function isSafeUrl(url) {
  // Проверка на javascript: URLs, которые могут привести к XSS
  if (!url) return false;

  const trimmed = url.trim().toLowerCase();
  if (trimmed.startsWith('javascript:') ||
      trimmed.startsWith('data:') ||
      trimmed.startsWith('vbscript:')) {
    return false;
  }

  return true;
}

/**
 * Рендерит текст с markdown-разметкой в HTML
 * @param {string} text - Текст с markdown-разметкой
 * @returns {string} - HTML для безопасного отображения
 */
export function renderMarkdown(text) {
  if (!text) return '';

  // Предварительный эскейп всего HTML для предотвращения XSS
  let html = escapeHtml(text);

  // Обработка заголовков
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Обработка стилей текста
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\_\_(.+?)\_\_/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/\_(.+?)\_/g, '<em>$1</em>');
  html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');

  // Обработка блоков кода
  html = html.replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Обработка изображений с проверкой URL и добавлением класса для модального окна
  html = html.replace(/!\[([^\]]+)\]\(([^)]+)\)/g, (match, alt, src) => {
    const safeAlt = escapeHtml(alt);
    const safeSrc = isSafeUrl(src) ? escapeHtml(src) : '';

    if (!safeSrc) {
      return `[Недопустимая ссылка на изображение]`;
    }

    return `<img src="${safeSrc}" alt="${safeAlt}" class="markdown-image clickable-image">`;
  });

  // Обработка ссылок с проверкой URL
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
    const safeText = escapeHtml(text);
    const safeUrl = isSafeUrl(url) ? escapeHtml(url) : '';

    if (!safeUrl) {
      return safeText;
    }

    return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeText}</a>`;
  });

  // Обработка списков
  // Неупорядоченные списки
  html = html.replace(/^\* (.+)$/gm, '<ul><li>$1</li></ul>');
  html = html.replace(/^- (.+)$/gm, '<ul><li>$1</li></ul>');

  // Упорядоченные списки
  html = html.replace(/^\d+\. (.+)$/gm, '<ol><li>$1</li></ol>');

  // Исправление вложенных списков
  html = html.replace(/<\/ul>\s*<ul>/g, '');
  html = html.replace(/<\/ol>\s*<ol>/g, '');

  // Обработка цитат
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

  // Горизонтальная линия
  html = html.replace(/^---$/gm, '<hr>');

  // Переносы строк - преобразуем в <br> исключая блоки кода
  html = html.replace(/\n/g, '<br>');
  html = html.replace(/<pre><code>(.*?)<\/code><\/pre>/gs, function(match) {
    return match.replace(/<br>/g, '\n');
  });

  return html;
}

/**
 * Извлекает URL изображений из markdown-контента
 * @param {string} markdownContent - Текст с markdown-разметкой
 * @returns {string[]} - Массив URL изображений
 */
export function extractImageUrls(markdownContent) {
  if (!markdownContent) return [];

  const regex = /!\[([^\]]*)\]\(([^)]+)\)/g;
  const urls = [];
  let match;

  while ((match = regex.exec(markdownContent)) !== null) {
    const url = match[2];
    if (isSafeUrl(url)) {
      urls.push(url);
    }
  }

  return urls;
}

/**
 * Создает превью markdown с ограничением длины и сохранением первого изображения
 * @param {string} content - Markdown контент
 * @param {number} maxLength - Максимальная длина текста
 * @returns {Object} - Превью с thumbnail и html
 */
export function createMarkdownPreview(content, maxLength = 500) {
  if (!content) return { thumbnailImage: null, renderedContent: '' };

  // Ищем первое изображение
  const firstImageMatch = content.match(/!\[([^\]]+)\]\(([^)]+)\)/);

  // Извлекаем превью изображения, если есть
  let thumbnailImage = null;
  if (firstImageMatch && isSafeUrl(firstImageMatch[2])) {
    thumbnailImage = {
      alt: escapeHtml(firstImageMatch[1]),
      url: escapeHtml(firstImageMatch[2])
    };
  }

  // Обрезаем контент и удаляем первое изображение для предотвращения дублирования
  let truncatedContent = content;
  if (firstImageMatch) {
    truncatedContent = truncatedContent.replace(firstImageMatch[0], '');
  }

  // Ограничиваем длину контента
  if (truncatedContent.length > maxLength) {
    truncatedContent = truncatedContent.substr(0, maxLength);
    // Завершаем на границе слова
    const lastSpaceIndex = truncatedContent.lastIndexOf(' ');
    if (lastSpaceIndex > maxLength - 20) {
      truncatedContent = truncatedContent.substr(0, lastSpaceIndex);
    }
    truncatedContent += '...';
  }

  // Рендерим обрезанный контент
  const renderedContent = renderMarkdown(truncatedContent);

  return {
    thumbnailImage,
    renderedContent
  };
}