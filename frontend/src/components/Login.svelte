<script>
  import { navigate } from "svelte-routing";
  import { api } from "../stores/userStore";

  let username = "";
  let password = "";
  let error = "";
  let loading = false;

  async function handleSubmit() {
    error = "";
    loading = true;

    if (!username || !password) {
      error = "Пожалуйста, заполните все поля";
      loading = false;
      return;
    }

    const result = await api.login(username, password);

    if (result.success) {
      navigate("/", { replace: true });
    } else {
      error = result.error || "Ошибка авторизации";
    }

    loading = false;
  }
</script>

<div class="login-page">
  <div class="form-container">
    <h1>Вход в аккаунт</h1>

    {#if error}
      <div class="error-message">{error}</div>
    {/if}

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="username">Имя пользователя</label>
        <input
          type="text"
          id="username"
          bind:value={username}
          disabled={loading}
          placeholder="Введите имя пользователя"
          required
          autocomplete="username"
        />
      </div>

      <div class="form-group">
        <label for="password">Пароль</label>
        <input
          type="password"
          id="password"
          bind:value={password}
          disabled={loading}
          placeholder="Введите пароль"
          required
          autocomplete="current-password"
        />
      </div>

      <button type="submit" disabled={loading} class="submit-button">
        {loading ? 'Выполняется вход...' : 'Войти'}
      </button>
    </form>

    <div class="register-link">
      <p>Нет аккаунта? <a href="/register">Зарегистрироваться</a></p>
    </div>
  </div>
</div>

<style>
  .login-page {
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
    max-width: 500px;
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
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
    color: #495057;
  }

  input {
    width: 100%;
    padding: 0.75rem;
    font-size: 1rem;
    border: 1px solid #ced4da;
    border-radius: 4px;
  }

  input:focus {
    border-color: #80bdff;
    outline: 0;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
  }

  .submit-button {
    width: 100%;
    padding: 0.75rem 1rem;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .submit-button:hover:not(:disabled) {
    background-color: #0069d9;
  }

  .submit-button:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
  }

  .register-link {
    margin-top: 1.5rem;
    text-align: center;
  }

  .register-link a {
    color: #007bff;
    text-decoration: none;
  }

  .register-link a:hover {
    text-decoration: underline;
  }
</style>