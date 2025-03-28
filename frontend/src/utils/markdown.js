// markdown.js - добавляем поддержку для модального просмотра изображений

export function renderMarkdown(text) {
  if (!text) return '';

  // Security: First escape HTML to prevent XSS
  let html = escapeHtml(text);

  // Process markdown
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\_\_(.+?)\_\_/g, '<strong>$1</strong>');

  // Italic
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/\_(.+?)\_/g, '<em>$1</em>');

  // Strikethrough
  html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');

  // Code blocks
  html = html.replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

  // Images - модифицируем обработку изображений, добавляя класс для модального просмотра
  html = html.replace(/!\[([^\]]+)\]\(([^)]+)\)/g,
    '<img src="$2" alt="$1" class="markdown-image clickable-image" onclick="handleImageClick(this)">');

  // Lists
  // Unordered lists
  html = html.replace(/^\* (.+)$/gm, '<ul><li>$1</li></ul>');
  html = html.replace(/^- (.+)$/gm, '<ul><li>$1</li></ul>');

  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<ol><li>$1</li></ol>');

  // Fix repeated list tags
  html = html.replace(/<\/ul>\s*<ul>/g, '');
  html = html.replace(/<\/ol>\s*<ol>/g, '');

  // Blockquotes
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr>');

  // Line breaks - convert newlines to <br> but not inside code blocks
  html = html.replace(/\n/g, '<br>');
  html = html.replace(/<pre><code>(.*?)<\/code><\/pre>/gs, function(match) {
    return match.replace(/<br>/g, '\n');
  });

  // Добавляем JavaScript для обработки кликов на изображениях
  html += `<script>
    function handleImageClick(img) {
      // Create modal if doesn't exist
      let modal = document.getElementById('image-modal');
      if (!modal) {
        modal = document.createElement('div');
        modal.id = 'image-modal';
        modal.className = 'image-modal';
        modal.innerHTML = '<div class="modal-content"><span class="close-modal">&times;</span><img id="modal-img"></div>';
        document.body.appendChild(modal);

        // Add close button handler
        modal.querySelector('.close-modal').onclick = function() {
          modal.style.display = 'none';
        };

        // Close when clicking outside the image
        modal.onclick = function(e) {
          if (e.target === modal) {
            modal.style.display = 'none';
          }
        };

        // Add ESC key handler
        document.addEventListener('keydown', function(e) {
          if (e.key === 'Escape' && modal.style.display === 'flex') {
            modal.style.display = 'none';
          }
        });
      }

      // Set the image source and show modal
      document.getElementById('modal-img').src = img.src;
      modal.style.display = 'flex';
    }
  </script>
  <style>
    .clickable-image {
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .clickable-image:hover {
      opacity: 0.9;
    }
    .image-modal {
      display: none;
      position: fixed;
      z-index: 9999;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.9);
      align-items: center;
      justify-content: center;
    }
    .modal-content {
      position: relative;
      max-width: 90%;
      max-height: 90%;
    }
    .modal-content img {
      max-width: 100%;
      max-height: 90vh;
      margin: auto;
      display: block;
    }
    .close-modal {
      position: absolute;
      top: -40px;
      right: 0;
      color: #f1f1f1;
      font-size: 40px;
      font-weight: bold;
      cursor: pointer;
    }
  </style>`;

  return html;
}

function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Function to extract image URLs from markdown content
export function extractImageUrls(markdownContent) {
  const regex = /!\[([^\]]*)\]\(([^)]+)\)/g;
  const urls = [];
  let match;

  while ((match = regex.exec(markdownContent)) !== null) {
    urls.push(match[2]);
  }

  return urls;
}