<script>
  import { navigate } from "svelte-routing";
  import { api } from "../stores/userStore";

  let username = "";
  let email = "";
  let password = "";
  let confirmPassword = "";
  let error = "";
  let loading = false;
  let success = false;

  async function handleSubmit() {
    error = "";
    loading = true;

    // Валидация полей
    if (!username || !email || !password || !confirmPassword) {
      error = "Пожалуйста, заполните все поля";
      loading = false;
      return;
    }

    if (password !== confirmPassword) {
      error = "Пароли не совпадают";
      loading = false;
      return;
    }

    if (password.length < 6) {
      error = "Пароль должен быть не менее 6 символов";
      loading = false;
      return;
    }

    // Проверка формата email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      error = "Некорректный формат email";
      loading = false;
      return;
    }

    const result = await api.register(username, email, password);

    if (result.success) {
      success = true;
      setTimeout(() => {
        navigate("/login", { replace: true });
      }, 2000);
    } else {
      error = result.error || "Ошибка регистрации";
    }

    loading = false;
  }
</script>

<div class="register-page">
  <div class="form-container">
    <h1>Регистрация</h1>

    {#if error}
      <div class="error-message">{error}</div>
    {/if}

    {#if success}
      <div class="success-message">
        Регистрация успешна! Перенаправление на страницу входа...
      </div>
    {/if}

    <form on:submit|preventDefault={handleSubmit} class:hidden={success}>
      <div class="form-group">
        <label for="username">Имя пользователя</label>
        <input
          type="text"
          id="username"
          bind:value={username}
          disabled={loading}
          placeholder="Придумайте имя пользователя"
          required
          autocomplete="username"
        />
      </div>

      <div class="form-group">
        <label for="email">Email</label>
        <input
          type="email"
          id="email"
          bind:value={email}
          disabled={loading}
          placeholder="Введите ваш email"
          required
          autocomplete="email"
        />
      </div>

      <div class="form-group">
        <label for="password">Пароль</label>
        <input
          type="password"
          id="password"
          bind:value={password}
          disabled={loading}
          placeholder="Придумайте пароль"
          required
          minlength="6"
          autocomplete="new-password"
        />
      </div>

      <div class="form-group">
        <label for="confirmPassword">Подтвердите пароль</label>
        <input
          type="password"
          id="confirmPassword"
          bind:value={confirmPassword}
          disabled={loading}
          placeholder="Введите пароль еще раз"
          required
          autocomplete="new-password"
        />
      </div>

      <button type="submit" disabled={loading} class="submit-button">
        {loading ? 'Регистрация...' : 'Зарегистрироваться'}
      </button>
    </form>

    <div class="login-link" class:hidden={success}>
      <p>Уже есть аккаунт? <a href="/login">Войти</a></p>
    </div>
  </div>
</div>

<style>
  .register-page {
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

  .success-message {
    background-color: #d4edda;
    color: #155724;
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

  .login-link {
    margin-top: 1.5rem;
    text-align: center;
  }

  .login-link a {
    color: #007bff;
    text-decoration: none;
  }

  .login-link a:hover {
    text-decoration: underline;
  }

  .hidden {
    display: none;
  }
</style>