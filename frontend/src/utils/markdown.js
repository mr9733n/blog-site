// markdown.js
// Simple markdown parser for basic formatting

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

  // Images
  html = html.replace(/!\[([^\]]+)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="markdown-image">');

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