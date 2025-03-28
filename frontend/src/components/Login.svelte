<script>
  import { Link, navigate } from "svelte-routing";
  import { api, userStore } from "../stores/userStore";

  let username = "";
  let password = "";
  let loading = false;
  let error = null;
  let hasSpecialChars = false;

  // Проверка наличия подозрительных символов в полях формы
  $: hasSpecialChars = /['";]/.test(username) || /['";]/.test(password);

  async function handleSubmit() {
    error = null;
    loading = true;

    // Проверка наличия небезопасных символов
    if (hasSpecialChars) {
      error = "Логин или пароль содержат недопустимые символы";
      loading = false;
      return;
    }

    const result = await api.login(username, password);

    if (result.success) {
      navigate("/", { replace: true });
    } else {
      error = result.error;
      loading = false;
    }
  }
</script>

<div class="login-page">
  <div class="login-form">
    <h1>Вход в аккаунт</h1>

    {#if error}
      <div class="error-message">{error}</div>
    {/if}

    {#if hasSpecialChars}
      <div class="warning-message">
        Обнаружены специальные символы, которые могут быть небезопасны.
      </div>
    {/if}

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="username">Имя пользователя</label>
        <input
          type="text"
          id="username"
          bind:value={username}
          disabled={loading}
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
          required
          autocomplete="current-password"
        />
      </div>

      <button type="submit" disabled={loading || hasSpecialChars}>
        {loading ? 'Выполняется вход...' : 'Войти'}
      </button>
    </form>

    <div class="form-footer">
      <p>Еще нет аккаунта? <Link to="/register">Зарегистрироваться</Link></p>
    </div>
  </div>
</div>

<style>
  .login-page {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2rem 0;
  }

  .login-form {
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem 3.5rem 2rem 2rem;
    width: 100%;
    max-width: 400px;
  }

  h1 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    text-align: center;
    color: #333;
    font-size: 1.8rem;
  }

  .error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border-radius: 4px;
    text-align: center;
  }

  .warning-message {
    background-color: #fff3cd;
    color: #856404;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border-radius: 4px;
    text-align: center;
    font-size: 0.9rem;
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

  button {
    width: 100%;
    padding: 0.75rem;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  button:hover:not(:disabled) {
    background-color: #0069d9;
  }

  button:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
  }

  .form-footer {
    margin-top: 1.5rem;
    text-align: center;
    color: #6c757d;
    font-size: 0.9rem;
  }

  .form-footer a {
    color: #007bff;
    text-decoration: none;
  }

  .form-footer a:hover {
    text-decoration: underline;
  }
</style>