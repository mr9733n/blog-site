<script>
  import { onMount } from "svelte";
  import { Link, navigate } from "svelte-routing";
  import { api, userStore } from "../stores/userStore";

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

  userStore.subscribe(value => {
    user = value;
  });

  onMount(async () => {
    try {
      post = await api.getPost(id);
      loading = false;

      // Загрузка комментариев
      await loadComments();
    } catch (err) {
      error = err.message;
      loading = false;
    }
  });

  // Функция для загрузки комментариев
  async function loadComments() {
    commentsLoading = true;
    try {
      comments = await api.getPostComments(id);
      commentsLoading = false;
    } catch (err) {
      commentError = "Не удалось загрузить комментарии";
      commentsLoading = false;
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

  // Удаление комментария
  async function deleteComment(commentId) {
    if (confirm("Вы уверены, что хотите удалить этот комментарий?")) {
      commentsLoading = true;

      try {
        await api.deleteComment(commentId);
        await loadComments();
      } catch (err) {
        commentError = err.message;
        commentsLoading = false;
      }
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
    return user && post && post.author_id === user.id;
  }
</script>

<div class="blog-post">
  {#if loading}
    <div class="loading">Загрузка поста...</div>
  {:else if error}
    <div class="error">
      <p>{error}</p>
      <Link to="/">Вернуться на главную</Link>
    </div>
  {:else if post}
    <article>
      <header>
        <h1>{post.title}</h1>
        <div class="post-meta">
          <div class="post-author">
            Автор: <span>{post.username}</span>
          </div>
          <div class="post-date">
            Опубликовано: <time>{formatDate(post.created_at)}</time>
          </div>
        </div>
      </header>

      <div class="post-content">
        {#each post.content.split('\n') as paragraph}
          <p>{paragraph}</p>
        {/each}
      </div>

      <footer>
        {#if isAuthor()}
          <div class="post-actions">
            {#if confirmDelete}
              <div class="confirm-delete">
                <p>Вы уверены, что хотите удалить этот пост?</p>
                <div class="confirm-buttons">
                  <button class="btn-delete" on:click={deletePost}>Да, удалить</button>
                  <button class="btn-cancel" on:click={cancelDelete}>Отмена</button>
                </div>
              </div>
            {:else}
              <Link to={`/edit/${post.id}`} class="btn-edit">Редактировать</Link>
              <button class="btn-delete" on:click={deletePost}>Удалить</button>
            {/if}
          </div>
        {/if}
      </footer>
    </article>

    <div class="back-link">
      <Link to="/">← Вернуться к списку постов</Link>
    </div>

    <!-- Секция комментариев -->
    <section class="comments-section">
      <h2>Комментарии ({comments.length})</h2>

      {#if commentError}
        <div class="comment-error">{commentError}</div>
      {/if}

      <!-- Форма для добавления нового комментария -->
      {#if user}
        <div class="comment-form">
          <textarea
            bind:value={newComment}
            placeholder="Напишите ваш комментарий..."
            rows="3"
          ></textarea>
          <button on:click={addComment} disabled={commentsLoading}>
            {commentsLoading ? 'Отправка...' : 'Отправить комментарий'}
          </button>
        </div>
      {:else}
        <div class="login-to-comment">
          <Link to="/login">Войдите</Link>, чтобы оставить комментарий
        </div>
      {/if}

      <!-- Список комментариев -->
      <div class="comments-list">
        {#if commentsLoading && comments.length === 0}
          <div class="comments-loading">Загрузка комментариев...</div>
        {:else if comments.length === 0}
          <div class="no-comments">Пока нет комментариев. Будьте первым, кто оставит комментарий!</div>
        {:else}
          {#each comments as comment}
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
                    <button class="save-btn" on:click={() => saveEditedComment(comment.id)}>Сохранить</button>
                    <button class="cancel-btn" on:click={cancelEditComment}>Отмена</button>
                  </div>
                </div>
              {:else}
                <div class="comment-content">{comment.content}</div>
              {/if}

              {#if user && (user.id === comment.author_id || user.id === post.author_id)}
                <div class="comment-actions">
                  {#if user.id === comment.author_id && editingCommentId !== comment.id}
                    <button class="edit-comment-btn" on:click={() => startEditComment(comment)}>
                      Редактировать
                    </button>
                  {/if}
                  <button class="delete-comment-btn" on:click={() => deleteComment(comment.id)}>
                    Удалить
                  </button>
                </div>
              {/if}
            </div>
          {/each}
        {/if}
      </div>
    </section>
  {/if}
</div>

<style>
  .blog-post {
    max-width: 800px;
    margin: 0 auto;
  }

  .loading, .error {
    text-align: center;
    padding: 2rem;
    background-color: #f8f9fa;
    border-radius: 5px;
    margin-bottom: 2rem;
  }

  .error {
    color: #721c24;
    background-color: #f8d7da;
  }

  .error a {
    display: inline-block;
    margin-top: 1rem;
    color: #721c24;
    font-weight: bold;
  }

  article {
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    margin-bottom: 2rem;
  }

  header {
    margin-bottom: 2rem;
  }

  h1 {
    margin-top: 0;
    margin-bottom: 1rem;
    color: #333;
    font-size: 2.2rem;
  }

  .post-meta {
    color: #6c757d;
    font-size: 0.9rem;
  }

  .post-author, .post-date {
    margin-bottom: 0.5rem;
  }

  .post-author span {
    font-weight: bold;
  }

  .post-content {
    line-height: 1.7;
    color: #212529;
    margin-bottom: 2rem;
  }

  footer {
    border-top: 1px solid #dee2e6;
    padding-top: 1.5rem;
    margin-top: 2rem;
  }

  .post-actions {
    display: flex;
    gap: 1rem;
  }

  .confirm-delete {
    background-color: #f8d7da;
    border-radius: 5px;
    padding: 1rem;
    width: 100%;
  }

  .confirm-delete p {
    margin-top: 0;
    margin-bottom: 1rem;
    font-weight: bold;
    color: #721c24;
  }

  .confirm-buttons {
    display: flex;
    gap: 1rem;
  }

  .btn-edit, .btn-delete, .btn-cancel {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    font-size: 0.9rem;
    text-decoration: none;
    cursor: pointer;
    display: inline-block;
  }

  .btn-edit {
    background-color: #17a2b8;
    color: white;
    border: none;
  }

  .btn-delete {
    background-color: #dc3545;
    color: white;
    border: none;
  }

  .btn-cancel {
    background-color: #6c757d;
    color: white;
    border: none;
  }

  .back-link {
    margin-bottom: 2rem;
  }

  .back-link a {
    color: #007bff;
    text-decoration: none;
  }

  .back-link a:hover {
    text-decoration: underline;
  }

  /* Стили для секции комментариев */
  .comments-section {
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    margin-bottom: 2rem;
  }

  .comments-section h2 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    font-size: 1.5rem;
    color: #333;
  }

  .comment-error {
    background-color: #f8d7da;
    color: #721c24;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border-radius: 4px;
  }

  .comment-form {
    margin-bottom: 2rem;
  }

  .comment-form textarea {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid #ced4da;
    border-radius: 4px;
    resize: vertical;
    font-family: inherit;
  }

  .comment-form button {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
  }

  .comment-form button:hover:not(:disabled) {
    background-color: #0069d9;
  }

  .comment-form button:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
  }

  .login-to-comment {
    margin-bottom: 2rem;
    padding: 1rem;
    background-color: #f8f9fa;
    border-radius: 4px;
    text-align: center;
  }

  .login-to-comment a {
    color: #007bff;
    text-decoration: none;
    font-weight: bold;
  }

  .comments-loading, .no-comments {
    text-align: center;
    padding: 1.5rem;
    background-color: #f8f9fa;
    border-radius: 4px;
    color: #6c757d;
  }

  .comments-list {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .comment {
    padding: 1.5rem;
    background-color: #f8f9fa;
    border-radius: 4px;
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
    color: #495057;
  }

  .comment-date {
    color: #6c757d;
  }

  .comment-content {
    line-height: 1.5;
    color: #212529;
    white-space: pre-line;
  }

  .comment-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    justify-content: flex-end;
  }

  .edit-comment-btn, .delete-comment-btn {
    background: none;
    border: none;
    color: #6c757d;
    cursor: pointer;
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
  }

  .edit-comment-btn:hover {
    color: #17a2b8;
  }

  .delete-comment-btn:hover {
    color: #dc3545;
  }

  .comment-edit-form {
    margin-top: 1rem;
  }

  .comment-edit-form textarea {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid #ced4da;
    border-radius: 4px;
    resize: vertical;
    font-family: inherit;
  }

  .comment-edit-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .save-btn, .cancel-btn {
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.8rem;
    cursor: pointer;
    border: none;
  }

  .save-btn {
    background-color: #28a745;
    color: white;
  }

  .save-btn:hover {
    background-color: #218838;
  }

  .cancel-btn {
    background-color: #6c757d;
    color: white;
  }

  .cancel-btn:hover {
    background-color: #5a6268;
  }
</style>