<script>
  import { onMount } from "svelte";
  import { Link, navigate } from "svelte-routing";
  import { api, userStore } from "../stores/userStore";
  import { renderMarkdown } from "../utils/markdown";

  export let id; // ID поста из параметра маршрута

  let post = null;
  let comments = [];
  let newComment = "";
  let loading = true;
  let commentsLoading = false;
  let error = null;
  let commentError = null;
  let user = null;
  let confirmDelete = false;
  let editingCommentId = null;
  let editCommentContent = "";
  let isSaved = false;
  let currentPage = 1;
  let commentsPerPage = 5;
  let totalPages = 1;
  let paginatedComments = [];
  let deletingCommentId = null; // Для отслеживания комментария, который собираются удалить
  let renderedContent = ''; // For storing the rendered markdown content

  userStore.subscribe(value => {
    user = value;
  });

  onMount(async () => {
    try {
      post = await api.getPost(id);
      // Render markdown content
      renderedContent = renderMarkdown(post.content);
      loading = false;

      // Загрузка комментариев
      await loadComments();
      if (post && user) {
        await checkIfSaved();
      }
    } catch (err) {
      error = err.message;
      loading = false;
    }
  });

  async function checkIfSaved() {
    if (user && post) {
      try {
        isSaved = await api.isPostSaved(post.id);
      } catch (err) {
        console.error("Ошибка проверки сохранения:", err);
      }
    }
  }

  async function savePost() {
    try {
      await api.savePost(post.id);
      isSaved = true;
    } catch (err) {
      error = err.message;
    }
  }

  async function unsavePost() {
    try {
      await api.unsavePost(post.id);
      isSaved = false;
    } catch (err) {
      error = err.message;
    }
  }

  // Функция для загрузки комментариев
  async function loadComments() {
    commentsLoading = true;
    try {
      comments = await api.getPostComments(id);
      applyPagination(); // Применяем пагинацию после загрузки комментариев
      commentsLoading = false;
    } catch (err) {
      commentError = "Не удалось загрузить комментарии";
      commentsLoading = false;
    }
  }

  // Функция для применения пагинации
  function applyPagination() {
    totalPages = Math.ceil(comments.length / commentsPerPage);
    // Ограничиваем текущую страницу
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    // Вычисляем комментарии для текущей страницы
    const startIndex = (currentPage - 1) * commentsPerPage;
    const endIndex = startIndex + commentsPerPage;
    paginatedComments = comments.slice(startIndex, endIndex);
  }

  // Переход к предыдущей странице
  function previousPage() {
    if (currentPage > 1) {
      currentPage--;
      applyPagination();
    }
  }

  // Переход к следующей странице
  function nextPage() {
    if (currentPage < totalPages) {
      currentPage++;
      applyPagination();
    }
  }

  // Добавление нового комментария
  async function addComment() {
    if (!user) {
      navigate('/login');
      return;
    }

    if (!newComment.trim()) {
      commentError = "Комментарий не может быть пустым";
      return;
    }

    commentError = null;
    commentsLoading = true;

    try {
      await api.addComment(id, newComment);
      newComment = "";
      await loadComments();
    } catch (err) {
      commentError = err.message;
      commentsLoading = false;
    }
  }

  // Начать редактирование комментария
  function startEditComment(comment) {
    editingCommentId = comment.id;
    editCommentContent = comment.content;
  }

  // Отменить редактирование комментария
  function cancelEditComment() {
    editingCommentId = null;
    editCommentContent = "";
  }

  // Сохранить отредактированный комментарий
  async function saveEditedComment(commentId) {
    if (!editCommentContent.trim()) {
      commentError = "Комментарий не может быть пустым";
      return;
    }

    commentError = null;
    commentsLoading = true;

    try {
      await api.updateComment(commentId, editCommentContent);
      editingCommentId = null;
      editCommentContent = "";
      await loadComments();
    } catch (err) {
      commentError = err.message;
      commentsLoading = false;
    }
  }

  // Функции для инлайн-удаления комментариев
  function startDeleteComment(commentId) {
    deletingCommentId = commentId;
  }

  function cancelDeleteComment() {
    deletingCommentId = null;
  }

  async function confirmDeleteComment(commentId) {
    commentsLoading = true;

    try {
      await api.deleteComment(commentId);
      deletingCommentId = null; // Сбрасываем после успешного удаления
      await loadComments();
    } catch (err) {
      commentError = err.message;
      commentsLoading = false;
    }
  }

  // Функция для форматирования даты
  function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('ru', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }

  // Функция для удаления поста
  async function deletePost() {
    if (!confirmDelete) {
      confirmDelete = true;
      return;
    }

    try {
      await api.deletePost(id);
      navigate("/", { replace: true });
    } catch (err) {
      error = err.message;
    }
  }

  // Отмена удаления
  function cancelDelete() {
    confirmDelete = false;
  }

  // Проверка, является ли пользователь автором поста
  function isAuthor() {
    return user && post && post.author_id === parseInt(user.id);
  }

  function canDeleteComment(comment) {
    if (!user || !comment) return false;

    // Проверяем, является ли пользователь автором комментария или автором поста
    const userId = parseInt(user.id);
    const commentAuthorId = parseInt(comment.author_id);
    const postAuthorId = parseInt(post.author_id);

    return userId === commentAuthorId || userId === postAuthorId;
  }

  function canEditComment(comment) {
    if (!user || !comment) return false;

    // Только автор комментария может его редактировать
    const userId = parseInt(user.id);
    const commentAuthorId = parseInt(comment.author_id);

    return userId === commentAuthorId;
  }

  function sanitizeHTML(str) {
    const temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
  }

  // Обновляем пагинацию при изменении комментариев
  $: if (comments) {
    applyPagination();
  }
</script>

<div class="blog-post">
  {#if loading}
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>Загрузка поста...</p>
    </div>
  {:else if error}
    <div class="alert alert-danger">
      <p>{error}</p>
      <Link to="/">Вернуться на главную</Link>
    </div>
  {:else if post}
    <article class="post-card">
      <header>
        <h1>{post.title}</h1>
        <div class="post-meta">
          <div class="post-author">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            <span>{post.username}</span>
          </div>
          <div class="post-date">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <time>{formatDate(post.created_at)}</time>
          </div>
          {#if user}
            <div class="post-save-action">
              {#if isSaved}
                <button class="btn-unsave" on:click={unsavePost}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                  </svg>
                  Удалить из сохранённых
                </button>
              {:else}
                <button class="btn-save" on:click={savePost}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                  </svg>
                  Сохранить
                </button>
              {/if}
            </div>
          {/if}
        </div>
      </header>

      <div class="post-content markdown-content">
        {@html renderedContent}
      </div>

      <footer>
        {#if isAuthor()}
          <div class="post-actions">
            {#if confirmDelete}
              <div class="confirm-delete">
                <p>Вы уверены, что хотите удалить этот пост?</p>
                <div class="confirm-buttons">
                  <button class="btn btn-danger" on:click={deletePost}>Да, удалить</button>
                  <button class="btn btn-secondary" on:click={cancelDelete}>Отмена</button>
                </div>
              </div>
            {:else}
              <Link to={`/edit/${post.id}`} class="btn btn-primary">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
                Редактировать
              </Link>
              <button class="btn btn-danger" on:click={deletePost}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  <line x1="10" y1="11" x2="10" y2="17"></line>
                  <line x1="14" y1="11" x2="14" y2="17"></line>
                </svg>
                Удалить
              </button>
            {/if}
          </div>
        {/if}
      </footer>
    </article>

    <div class="back-link">
      <Link to="/" class="btn btn-link">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        Вернуться к списку постов
      </Link>
    </div>

    <!-- Секция комментариев -->
    <section class="comments-section">
      <h2>Комментарии ({comments.length})</h2>

      {#if commentError}
        <div class="alert alert-danger">{commentError}</div>
      {/if}

      <!-- Список комментариев -->
      <div class="comments-list">
        {#if commentsLoading && comments.length === 0}
          <div class="loading-container">
            <div class="loading-spinner"></div>
            <p>Загрузка комментариев...</p>
          </div>
        {:else if comments.length === 0}
          <div class="no-comments">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <p>Пока нет комментариев. Будьте первым, кто оставит комментарий!</p>
          </div>
        {:else}
          {#each paginatedComments as comment}
            <div class="comment">
              <div class="comment-header">
                <div class="comment-author">{comment.username}</div>
                <div class="comment-date">{formatDate(comment.created_at)}</div>
              </div>

              {#if editingCommentId === comment.id}
                <div class="comment-edit-form">
                  <textarea
                    bind:value={editCommentContent}
                    rows="3"
                  ></textarea>
                  <div class="comment-edit-actions">
                    <button class="btn btn-primary btn-sm" on:click={() => saveEditedComment(comment.id)}>Сохранить</button>
                    <button class="btn btn-secondary btn-sm" on:click={cancelEditComment}>Отмена</button>
                  </div>
                </div>
              {:else}
                <div class="comment-content">{@html sanitizeHTML(comment.content)}</div>
              {/if}

              {#if user && canDeleteComment(comment)}
                <div class="comment-actions">
                  {#if canEditComment(comment) && editingCommentId !== comment.id && deletingCommentId !== comment.id}
                    <button class="btn btn-link btn-sm" on:click={() => startEditComment(comment)}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                      </svg>
                      Редактировать
                    </button>
                  {/if}

                  {#if deletingCommentId === comment.id}
                    <div class="delete-confirmation">
                      <p>Вы уверены, что хотите удалить этот комментарий?</p>
                      <div class="delete-actions">
                        <button class="btn btn-danger btn-sm" on:click={() => confirmDeleteComment(comment.id)}>
                          Да, удалить
                        </button>
                        <button class="btn btn-secondary btn-sm" on:click={cancelDeleteComment}>
                          Отмена
                        </button>
                      </div>
                    </div>
                  {:else if editingCommentId !== comment.id}
                    <button class="btn btn-link btn-sm text-danger" on:click={() => startDeleteComment(comment.id)}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        <line x1="10" y1="11" x2="10" y2="17"></line>
                        <line x1="14" y1="11" x2="14" y2="17"></line>
                      </svg>
                      Удалить
                    </button>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}

          <!-- Пагинация -->
          {#if totalPages > 1}
            <div class="pagination">
              <button
                class="btn btn-secondary"
                on:click={previousPage}
                disabled={currentPage === 1}
              >
                &laquo; Предыдущая
              </button>
              <span class="pagination-info">Страница {currentPage} из {totalPages}</span>
              <button
                class="btn btn-secondary"
                on:click={nextPage}
                disabled={currentPage === totalPages}
              >
                Следующая &raquo;
              </button>
            </div>
          {/if}
        {/if}
      </div>

      <!-- Форма для добавления нового комментария -->
      {#if user}
        <div class="comment-form">
          <h3>Добавить комментарий</h3>
          <textarea
            bind:value={newComment}
            placeholder="Напишите ваш комментарий..."
            rows="3"
          ></textarea>
          <button class="btn btn-primary" on:click={addComment} disabled={commentsLoading}>
            {commentsLoading ? 'Отправка...' : 'Отправить комментарий'}
          </button>
        </div>
      {:else}
        <div class="login-to-comment">
          <Link to="/login">Войдите</Link>, чтобы оставить комментарий
        </div>
      {/if}
    </section>
  {/if}
</div>

<style>
  .blog-post {
    max-width: 800px;
    margin: 0 auto;
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    background-color: var(--bg-secondary);
    border-radius: 5px;
    margin-bottom: 2rem;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--border-color);
    border-top: 4px solid var(--accent-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .post-card {
    background-color: var(--bg-secondary);
    border-radius: 5px;
    box-shadow: var(--card-shadow);
    padding: 2rem;
    margin-bottom: 2rem;
  }

  h1 {
    margin-top: 0;
    margin-bottom: 1rem;
    color: var(--text-primary);
    font-size: 2.2rem;
  }

  .post-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 2rem;
    color: var(--text-secondary);
  }

  .post-author, .post-date {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
  }

  .post-author span {
    font-weight: bold;
  }

  .post-content {
    line-height: 1.7;
    color: var(--text-primary);
    margin-bottom: 2rem;
  }

  /* Markdown specific styling */
  :global(.markdown-content h1) {
    font-size: 1.8rem;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 0.5rem;
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

  footer {
    border-top: 1px solid var(--border-color);
    padding-top: 1.5rem;
    margin-top: 2rem;
  }

  .post-actions {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .confirm-delete {
    background-color: var(--danger-bg);
    border-radius: 5px;
    padding: 1rem;
    width: 100%;
  }

  .confirm-delete p {
    margin-top: 0;
    margin-bottom: 1rem;
    font-weight: bold;
    color: var(--danger-text);
  }

  .confirm-buttons {
    display: flex;
    gap: 1rem;
  }

  .back-link {
    margin-bottom: 2rem;
  }

  .back-link :global(a) {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--accent-color);
    text-decoration: none;
    font-weight: 500;
  }

  .back-link :global(a:hover) {
    text-decoration: underline;
  }

  /* Comment styles */
  .comments-section {
    background-color: var(--bg-secondary);
    border-radius: 5px;
    box-shadow: var(--card-shadow);
    padding: 2rem;
    margin-bottom: 2rem;
  }

  .comments-section h2 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    font-size: 1.5rem;
    color: var(--text-primary);
  }

  .comments-list {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .no-comments {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2rem;
    background-color: var(--bg-primary);
    border-radius: 5px;
    color: var(--text-secondary);
    text-align: center;
  }

  .no-comments svg {
    margin-bottom: 1rem;
  }

  .comment {
    padding: 1.5rem;
    background-color: var(--bg-primary);
    border-radius: 5px;
    position: relative;
  }

  .comment-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
  }

  .comment-author {
    font-weight: bold;
    color: var(--text-primary);
  }

  .comment-date {
    color: var(--text-secondary);
  }

  .comment-content {
    line-height: 1.5;
    color: var(--text-primary);
    white-space: pre-line;
  }

  .comment-actions {
    display: flex;
    gap: 1rem;
    margin-top: 1rem;
    justify-content: flex-end;
  }

  .comment-edit-form {
    margin-top: 1rem;
  }

  .comment-edit-form textarea {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    resize: vertical;
    background-color: var(--bg-secondary);
    color: var(--text-primary);
  }

  .comment-edit-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .delete-confirmation {
    margin-top: 1rem;
    background-color: var(--danger-bg);
    border-radius: 4px;
    padding: 0.75rem;
  }

  .delete-confirmation p {
    margin: 0 0 0.75rem 0;
    color: var(--danger-text);
    font-size: 0.9rem;
  }

  .delete-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1.5rem;
    padding: 0.5rem 0;
  }

  .pagination-info {
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  .comment-form {
    margin-top: 2rem;
  }

  .comment-form h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.25rem;
    color: var(--text-primary);
  }

  .comment-form textarea {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    resize: vertical;
    font-family: inherit;
    background-color: var(--bg-secondary);
    color: var(--text-primary);
  }

  .login-to-comment {
    margin-top: 2rem;
    padding: 1rem;
    background-color: var(--bg-primary);
    border-radius: 4px;
    text-align: center;
  }

  .login-to-comment :global(a) {
    color: var(--accent-color);
    text-decoration: none;
    font-weight: bold;
  }

  .login-to-comment :global(a:hover) {
    text-decoration: underline;
  }

  .btn-save, .btn-unsave {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    font-size: 0.9rem;
    cursor: pointer;
    border: none;
    transition: background-color 0.2s;
  }

  .btn-save {
    background-color: var(--accent-color);
    color: white;
  }

  .btn-save:hover {
    background-color: var(--accent-hover);
  }

  .btn-unsave {
    background-color: var(--btn-danger-bg);
    color: white;
  }

  .btn-unsave:hover {
    background-color: #c82333;
  }

  .btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
  }

  .btn-link {
    background: none;
    border: none;
    padding: 0;
    color: var(--accent-color);
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }

  .btn-link:hover {
    text-decoration: underline;
  }

  .text-danger {
    color: var(--btn-danger-bg) !important;
  }

  @media (max-width: 768px) {
    .post-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.5rem;
    }

    .post-actions {
      flex-direction: column;
      gap: 1rem;
    }

    .comment-header {
      flex-direction: column;
      align-items: flex-start;
    }

    h1 {
      font-size: 1.8rem;
    }

    .post-card, .comments-section {
      padding: 1.5rem;
    }

    .pagination {
      flex-direction: column;
      gap: 1rem;
    }
  }
</style>