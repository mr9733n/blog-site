<script>
  import { onMount } from "svelte";
  import { navigate } from "svelte-routing";
  import { checkTokenExpiration, logout, api, userStore } from "../stores/userStore";
  import { renderMarkdown } from "../utils/markdown";

  let title = "";
  let content = "";
  let error = "";
  let loading = false;
  let previewMode = false;
  let renderedPreview = "";
  let imageUploadProgress = null;
  let uploadedImages = [];

  // Проверка авторизации
  onMount(() => {
      const isValid = checkTokenExpiration();
    if (!isValid) {
      console.warn('🔒 Токен истёк — разлогиниваем');
      logout();
    }
    const unsubscribe = userStore.subscribe(user => {
      if (!user) {
        navigate("/login", { replace: true });
      }
    });

    return () => unsubscribe();
  });

  async function handleSubmit() {
    error = "";
    loading = true;

    // Валидация формы
    if (!title.trim()) {
      error = "Заголовок не может быть пустым";
      loading = false;
      return;
    }

    if (!content.trim()) {
      error = "Содержание поста не может быть пустым";
      loading = false;
      return;
    }

    try {
      await api.createPost(title, content);
      navigate("/", { replace: true });
    } catch (err) {
      error = err.message;
      loading = false;
    }
  }

  function togglePreview() {
    previewMode = !previewMode;
    if (previewMode) {
      renderedPreview = renderMarkdown(content);
    }
  }

  function insertMarkdown(tag) {
    const textarea = document.getElementById('content');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = content.substring(start, end);

    let insertion = '';

    switch(tag) {
      case 'bold':
        insertion = `**${selectedText || 'жирный текст'}**`;
        break;
      case 'italic':
        insertion = `*${selectedText || 'курсив'}*`;
        break;
      case 'h1':
        insertion = `\n# ${selectedText || 'Заголовок 1'}\n`;
        break;
      case 'h2':
        insertion = `\n## ${selectedText || 'Заголовок 2'}\n`;
        break;
      case 'h3':
        insertion = `\n### ${selectedText || 'Заголовок 3'}\n`;
        break;
      case 'link':
        insertion = `[${selectedText || 'текст ссылки'}](http://example.com)`;
        break;
    case 'image':
        if (uploadedImages.length > 0) {
            // Use the most recently uploaded image
            const lastImage = uploadedImages[uploadedImages.length - 1];
            // Вместо обертывания изображения в ссылку, просто вставляем само изображение
            insertion = `![${selectedText || lastImage.name}](${lastImage.url})`;
        } else {
            // No uploaded images, show error message
            error = "Пожалуйста, сначала загрузите изображение";
            return; // Exit without inserting anything
        }
        break;
      case 'code':
        insertion = `\`${selectedText || 'код'}\``;
        break;
      case 'codeblock':
        insertion = `\n\`\`\`\n${selectedText || 'блок кода'}\n\`\`\`\n`;
        break;
      case 'quote':
        insertion = `\n> ${selectedText || 'цитата'}\n`;
        break;
      case 'list':
        insertion = `\n- ${selectedText || 'элемент списка'}\n- элемент списка\n- элемент списка\n`;
        break;
      case 'ordered-list':
        insertion = `\n1. ${selectedText || 'элемент списка'}\n2. элемент списка\n3. элемент списка\n`;
        break;
      case 'hr':
        insertion = `\n---\n`;
        break;
      default:
        insertion = selectedText;
    }

    content = content.substring(0, start) + insertion + content.substring(end);

    // Set focus back to textarea and position cursor after insertion
    setTimeout(() => {
      textarea.focus();
      const newCursorPos = start + insertion.length;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  }

  // Function to handle file selection
async function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Проверка типа файла
  if (!file.type.startsWith('image/')) {
    error = "Выбранный файл не является изображением";
    return;
  }

  // Проверка размера файла
  if (file.size > 5 * 1024 * 1024) {
    error = "Размер файла не должен превышать 5MB";
    return;
  }

  // Очистка ошибок и показ индикатора загрузки
  error = "";
  imageUploadProgress = 0;

  try {
    // Вместо создания локального blob-URL, загружаем файл на сервер
    const simulateProgress = setInterval(() => {
      imageUploadProgress += 10;
      if (imageUploadProgress >= 90) clearInterval(simulateProgress);
    }, 100);

    // Загрузка файла на сервер через API
    const response = await api.uploadImage(file);
    clearInterval(simulateProgress);
    imageUploadProgress = 100;

    // Получаем URL изображения с сервера
    const imageUrl = response.image.url_path;

    // Добавляем в список загруженных изображений
    uploadedImages = [...uploadedImages, {
      name: file.filename || file.name,
      url: imageUrl,
      size: formatFileSize(file.size),
      id: response.image.id
    }];

    // Вставляем URL в markdown
    const insertion = `![${file.name}](${imageUrl})`;
    // ...код для вставки в текстовую область...

    // Сбрасываем индикатор прогресса
    setTimeout(() => {
      imageUploadProgress = null;
    }, 500);
  } catch (err) {
    error = "Ошибка загрузки изображения: " + err.message;
    imageUploadProgress = null;
  }
}

  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' bytes';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
  }
</script>

<div class="create-post">
  <div class="form-container">
    <h1>Создание нового поста</h1>

    {#if error}
      <div class="alert alert-danger">{error}</div>
    {/if}

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="title">Заголовок</label>
        <input
          type="text"
          id="title"
          bind:value={title}
          disabled={loading}
          placeholder="Введите заголовок поста"
          required
        />
      </div>

      <div class="form-group">
        <label for="content">Содержание</label>

        <div class="content-toolbar">
          <button type="button" on:click={() => insertMarkdown('bold')} title="Жирный">
            <strong>B</strong>
          </button>
          <button type="button" on:click={() => insertMarkdown('italic')} title="Курсив">
            <em>I</em>
          </button>
          <button type="button" on:click={() => insertMarkdown('h1')} title="Заголовок 1">H1</button>
          <button type="button" on:click={() => insertMarkdown('h2')} title="Заголовок 2">H2</button>
          <button type="button" on:click={() => insertMarkdown('h3')} title="Заголовок 3">H3</button>
          <button type="button" on:click={() => insertMarkdown('link')} title="Ссылка">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
          </button>
          <button type="button" on:click={() => insertMarkdown('image')} title="Изображение">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
          </button>
          <button type="button" on:click={() => insertMarkdown('code')} title="Код">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="16 18 22 12 16 6"></polyline>
              <polyline points="8 6 2 12 8 18"></polyline>
            </svg>
          </button>
          <button type="button" on:click={() => insertMarkdown('codeblock')} title="Блок кода">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M16 18l6-6-6-6M8 6l-6 6 6 6"/>
            </svg>
          </button>
          <button type="button" on:click={() => insertMarkdown('quote')} title="Цитата">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </button>
          <button type="button" on:click={() => insertMarkdown('list')} title="Список">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
              <line x1="3" y1="6" x2="3.01" y2="6"></line>
              <line x1="3" y1="12" x2="3.01" y2="12"></line>
              <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
          </button>
          <button type="button" on:click={() => insertMarkdown('ordered-list')} title="Нумерованный список">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
              <line x1="3" y1="6" x2="3.01" y2="6"></line>
              <line x1="3" y1="12" x2="3.01" y2="12"></line>
              <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
          </button>
          <button type="button" on:click={() => insertMarkdown('hr')} title="Горизонтальная линия">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>

          <div class="file-upload">
            <label for="image-upload" class="upload-btn" title="Загрузить изображение">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              Загрузить
            </label>
            <input
              type="file"
              id="image-upload"
              accept="image/*"
              on:change={handleFileSelect}
              disabled={imageUploadProgress !== null}
              style="display: none;"
            />
          </div>

          <button type="button" class="preview-toggle" on:click={togglePreview}>
            {previewMode ? 'Редактировать' : 'Предпросмотр'}
          </button>
        </div>

        {#if imageUploadProgress !== null}
          <div class="upload-progress">
            <div class="progress-bar" style="width: {imageUploadProgress}%"></div>
            <span>{imageUploadProgress}%</span>
          </div>
        {/if}

        {#if uploadedImages.length > 0}
          <div class="uploaded-images">
            <h4>Загруженные изображения:</h4>
            <ul>
              {#each uploadedImages as image}
                <li>
                  <a href={image.url} target="_blank" rel="noopener noreferrer">{image.name}</a>
                  <span>({image.size})</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if previewMode}
          <div class="content-preview markdown-content">
            {@html renderedPreview}
          </div>
        {:else}
          <textarea
            id="content"
            bind:value={content}
            disabled={loading}
            placeholder="Введите содержание поста... Поддерживается Markdown!"
            rows="15"
            required
          ></textarea>

          <div class="markdown-help">
            <p>Форматирование Markdown: **жирный**, *курсив*, # Заголовок, ## Подзаголовок, [ссылка](url), ![изображение](url), `код`, > цитата, - список</p>
          </div>
        {/if}
      </div>

      <div class="form-actions">
        <button type="button" class="btn btn-secondary" on:click={() => navigate('/')}>
          Отмена
        </button>
        <button type="submit" disabled={loading} class="btn btn-primary">
          {loading ? 'Сохранение...' : 'Опубликовать'}
        </button>
      </div>
    </form>
  </div>
</div>

<style>
  .create-post {
    display: flex;
    justify-content: center;
    padding: 2rem 0;
  }

  .form-container {
    background-color: var(--bg-secondary);
    border-radius: 5px;
    box-shadow: var(--card-shadow);
    padding: 2rem;
    width: 100%;
    max-width: 800px;
  }

  h1 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    text-align: center;
    color: var(--text-primary);
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
    color: var(--text-primary);
  }

  textarea {
    width: 100%;
    padding: 0.75rem;
    font-size: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-family: inherit;
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    resize: vertical;
  }

  .content-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 4px 4px 0 0;
    padding: 0.5rem;
    background-color: var(--bg-primary);
  }

  .content-toolbar button {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 3px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background-color 0.2s;
    color: var(--text-primary);
  }

  .content-toolbar button:hover {
    background-color: var(--bg-primary);
  }

  .preview-toggle {
    margin-left: auto !important;
    width: auto !important;
    padding: 0 0.75rem !important;
  }

  .content-preview {
    min-height: 300px;
    max-height: 600px;
    overflow-y: auto;
    padding: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 0 0 4px 4px;
    background-color: var(--bg-secondary);
    color: var(--text-primary);
  }

  .markdown-help {
    margin-top: 0.5rem;
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  .form-actions {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
  }

  .upload-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 3px;
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.9rem;
  }

  .upload-btn:hover {
    background-color: var(--bg-primary);
  }

  .upload-progress {
    margin-top: 0.5rem;
    height: 20px;
    background-color: var(--bg-primary);
    border-radius: 10px;
    overflow: hidden;
    position: relative;
  }

  .progress-bar {
    height: 100%;
    background-color: var(--accent-color);
    border-radius: 10px;
    transition: width 0.3s ease;
  }

  .upload-progress span {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.85rem;
    font-weight: bold;
    text-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
  }

  .uploaded-images {
    margin-top: 1rem;
    font-size: 0.9rem;
  }

  .uploaded-images h4 {
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1rem;
    color: var(--text-primary);
  }

  .uploaded-images ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .uploaded-images li {
    margin-bottom: 0.25rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .uploaded-images a {
    color: var(--accent-color);
    text-decoration: none;
  }

  .uploaded-images a:hover {
    text-decoration: underline;
  }

  .uploaded-images span {
    color: var(--text-secondary);
    font-size: 0.85rem;
  }

  /* Style for markdown content preview */
  :global(.markdown-content h1) {
    font-size: 1.8rem;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-color);
  }

  :global(.markdown-content h2) {
    font-size: 1.6rem;
    margin-top: 1.4rem;
    margin-bottom: 0.9rem;
  }

  :global(.markdown-content h3) {
    font-size: 1.4rem;
    margin-top: 1.3rem;
    margin-bottom: 0.8rem;
  }

  :global(.markdown-content p) {
    margin-bottom: 1rem;
  }

  :global(.markdown-content ul), :global(.markdown-content ol) {
    margin-bottom: 1rem;
    padding-left: 2rem;
  }

  :global(.markdown-content li) {
    margin-bottom: 0.5rem;
  }

  :global(.markdown-content blockquote) {
    border-left: 4px solid var(--accent-color);
    padding-left: 1rem;
    margin-left: 0;
    margin-right: 0;
    font-style: italic;
    color: var(--text-secondary);
  }

  :global(.markdown-content pre) {
    background-color: var(--bg-primary);
    border-radius: 4px;
    padding: 1rem;
    overflow-x: auto;
    margin-bottom: 1rem;
  }

  :global(.markdown-content code) {
    background-color: var(--bg-primary);
    border-radius: 3px;
    padding: 0.2rem 0.4rem;
    font-family: monospace;
  }

  :global(.markdown-content pre code) {
    padding: 0;
    background-color: transparent;
  }

  :global(.markdown-content img) {
    max-width: 100%;
    height: auto;
    border-radius: 5px;
    margin: 1rem 0;
  }

  :global(.markdown-content hr) {
    border: 0;
    height: 1px;
    background-color: var(--border-color);
    margin: 2rem 0;
  }

  @media (max-width: 768px) {
    .form-container {
      padding: 1.5rem;
    }

    .form-actions {
      flex-direction: column-reverse;
    }

    .content-toolbar {
      justify-content: center;
    }

    .preview-toggle {
      margin-top: 0.5rem;
      margin-left: 0 !important;
      width: 100% !important;
    }
  }
</style>