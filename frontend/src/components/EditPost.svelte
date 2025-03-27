<script>
  import { onMount } from "svelte";
  import { navigate } from "svelte-routing";
  import { api, userStore } from "../stores/userStore";

  export let id; // ID поста из параметра маршрута

  let title = "";
  let content = "";
  let error = "";
  let loading = true;
  let post = null;
  let user = null;

  userStore.subscribe(value => {
    user = value;
  });

  onMount(async () => {
    // Проверка авторизации
    if (!user) {
      navigate("/login", { replace: true });
      return;
    }

    try {
      // Загрузка информации о посте
      post = await api.getPost(id);

      // Проверка прав на редактирование
      if (post.author_id !== user.id) {
        navigate(`/post/${id}`, { replace: true });
        return;
      }

      // Заполнение полей формы
      title = post.title;
      content = post.content;
      loading = false;
    } catch (err) {
      error = err.message;
      loading = false;
    }
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
      await api.updatePost(id, title, content);
      navigate(`/post/${id}`, { replace: true });
    } catch (err) {
      error = err.message;
      loading = false;
    }
  }
</script>

<div class="edit-post">
  {#if loading && !error}
    <div class="loading">Загрузка поста...</div>
  {:else if error}
    <div class="error-message">{error}</div>
    <div class="back-link">
      <button on:click={() => history.back()} class="back-button">← Вернуться назад</button>
    </div>
  {:else}
    <div class="form-container">
      <h1>Редактирование поста</h1>

      {#if error}
        <div class="error-message">{error}</div>
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
          <textarea
            id="content"
            bind:value={content}
            disabled={loading}
            placeholder="Введите содержание поста..."
            rows="12"
            required
          ></textarea>
        </div>

        <div class="form-actions">
          <button type="button" class="cancel-button" on:click={() => navigate(`/post/${id}`)}>
            Отмена
          </button>
          <button type="submit" disabled={loading} class="submit-button">
            {loading ? 'Сохранение...' : 'Сохранить изменения'}
          </button>
        </div>
      </form>
    </div>
  {/if}
</div>

<style>
  .edit-post {
    display: flex;
    justify-content: center;
    padding: 2rem 0;
  }

  .loading {
    text-align: center;
    padding: 2rem;
    background-color: #f8f9fa;
    border-radius: 5px;
  }

  .form-container {
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    width: 100%;
    max-width: 800px;
  }

  h1 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    text-align: center;
    color: #333;
  }

  .error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border-radius: 4px;
    text-align: center;
  }

  .back-link {
    text-align: center;
    margin-top: 1rem;
  }

  .back-link a {
    color: #007bff;
    text-decoration: none;
  }

  .back-link a:hover {
    text-decoration: underline;
  }

  .back-link a, .back-button {
    color: #007bff;
    text-decoration: none;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    font-size: 1rem;
  }

  .back-link a:hover, .back-button:hover {
    text-decoration: underline;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
    color: #495057;
  }

  input, textarea {
    width: 100%;
    padding: 0.75rem;
    font-size: 1rem;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-family: inherit;
  }

  input:focus, textarea:focus {
    border-color: #80bdff;
    outline: 0;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
  }

  textarea {
    resize: vertical;
    min-height: 200px;
  }

  .form-actions {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
  }

  .submit-button, .cancel-button {
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.2s;
    flex: 1;
  }

  .submit-button {
    background-color: #28a745;
    color: white;
    border: none;
  }

  .submit-button:hover:not(:disabled) {
    background-color: #218838;
  }

  .submit-button:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
  }

  .cancel-button {
    background-color: #6c757d;
    color: white;
    border: none;
  }

  .cancel-button:hover {
    background-color: #5a6268;
  }
</style>