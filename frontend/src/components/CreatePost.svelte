<script>
  import { onMount } from "svelte";
  import { navigate } from "svelte-routing";
  import { api, userStore } from "../stores/userStore";

  let title = "";
  let content = "";
  let error = "";
  let loading = false;

  // Проверка авторизации
  onMount(() => {
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
</script>

<div class="create-post">
  <div class="form-container">
    <h1>Создание нового поста</h1>

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
        <button type="button" class="cancel-button" on:click={() => navigate('/')}>
          Отмена
        </button>
        <button type="submit" disabled={loading} class="submit-button">
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