<script>
  import { navigate } from "svelte-routing";
  import { login, register } from "../stores/authService";
  // Импортируем функции валидации
  import { validateUsername, validateEmail, validatePassword } from "../utils/validation";

  let username = "";
  let email = "";
  let password = "";
  let confirmPassword = "";
  let error = "";
  let loading = false;
  let success = false;
  let passwordStrength = 0; // Добавляем отслеживание силы пароля

  async function handleSubmit() {
    error = "";
    loading = true;

    // Валидация полей с использованием новых функций
    const usernameValidation = validateUsername(username);
    if (!usernameValidation.valid) {
      error = usernameValidation.error;
      loading = false;
      return;
    }

    const emailValidation = validateEmail(email);
    if (!emailValidation.valid) {
      error = emailValidation.error;
      loading = false;
      return;
    }

    const passwordValidation = validatePassword(password);
    if (!passwordValidation.valid) {
      error = passwordValidation.error;
      loading = false;
      return;
    }

    // Дополнительно сохраняем силу пароля для отображения
    passwordStrength = passwordValidation.strength || 0;

    // Проверка совпадения паролей
    if (password !== confirmPassword) {
      error = "Пароли не совпадают";
      loading = false;
      return;
    }

    const result = await register(username, email, password);

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

        <!-- Добавляем индикатор силы пароля, если пользователь ввел пароль -->
        {#if password.length > 0}
          <div class="password-strength">
            <div class="strength-bar">
              <div
                class="strength-indicator"
                style="width: {passwordStrength * 25}%; background-color: {
                  passwordStrength <= 1 ? '#dc3545' :
                  passwordStrength <= 2 ? '#ffc107' :
                  passwordStrength <= 3 ? '#6c757d' : '#28a745'
                }"
              ></div>
            </div>
            <div class="strength-text">
              {#if passwordStrength <= 1}
                Слабый
              {:else if passwordStrength <= 2}
                Средний
              {:else if passwordStrength <= 3}
                Хороший
              {:else}
                Отличный
              {/if}
            </div>
          </div>
        {/if}
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
    background-color: var(--bg-secondary);
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem 3.5rem 2rem 2rem;
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
    border: 1px solid #aea4ae;
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

  /* Стили для индикатора силы пароля */
  .password-strength {
    margin-top: 0.5rem;
    font-size: 0.85rem;
  }

  .strength-bar {
    height: 5px;
    background-color: #e9ecef;
    border-radius: 2px;
    margin-bottom: 0.25rem;
  }

  .strength-indicator {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s, background-color 0.3s;
  }

  .strength-text {
    text-align: right;
    font-size: 0.8rem;
    color: #6c757d;
  }
</style>