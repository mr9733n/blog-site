<!-- EditUser.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { api } from "../stores/apiService";
  import { userStore } from "../stores/userStore";
  import { isAdmin } from "../utils/authWrapper";
  // Импортируем функции валидации
  import { validateUsername, validateEmail, validatePassword } from "../utils/validation";

  export let userId;
  export let username;
  export let email;
  export let adminMode = false; // Prop to determine if in admin mode

  let newUsername = username;
  let newEmail = email;
  let newPassword = '';
  let confirmPassword = '';
  let currentPassword = '';
  let error = null;
  let success = null;
  let loading = false;
  let currentUser = null;
  let validationErrors = {}; // Объект для хранения ошибок каждого поля
  let showCurrentPasswordField = false; // Controls visibility of current password field

  userStore.subscribe(value => {
    currentUser = value;
  });

  // Determine if this is self-update or admin update
  $: isSelfUpdate = currentUser && currentUser.id === userId;
  // Show current password field if it's a self-update and either password is being changed or sensitive fields are modified
  $: showCurrentPasswordField = isSelfUpdate && (newPassword || newUsername !== username || newEmail !== email);

  const dispatch = createEventDispatcher();

  // Функция валидации всех полей формы
  function validateForm() {
    validationErrors = {};
    let isValid = true;

    // Валидация имени пользователя, если оно изменилось
    if (newUsername !== username) {
      const usernameValidation = validateUsername(newUsername);
      if (!usernameValidation.valid) {
        validationErrors.username = usernameValidation.error;
        isValid = false;
      }
    }

    // Валидация email, если он изменился
    if (newEmail !== email) {
      const emailValidation = validateEmail(newEmail);
      if (!emailValidation.valid) {
        validationErrors.email = emailValidation.error;
        isValid = false;
      }
    }

    // Валидация пароля, если он заполнен
    if (newPassword) {
      const passwordValidation = validatePassword(newPassword);
      if (!passwordValidation.valid) {
        validationErrors.password = passwordValidation.error;
        isValid = false;
      }

      // Проверка совпадения паролей
      if (newPassword !== confirmPassword) {
        validationErrors.confirmPassword = 'Пароли не совпадают';
        isValid = false;
      }
    }

    // Validate current password is provided if required
    if (showCurrentPasswordField && !currentPassword) {
      validationErrors.currentPassword = 'Для изменения профиля необходимо ввести текущий пароль';
      isValid = false;
    }

    return isValid;
  }

  // Функция сохранения изменений
  async function saveChanges() {
    // Очистка предыдущих сообщений
    error = null;
    success = null;

    // Валидация формы
    if (!validateForm()) {
      error = 'Пожалуйста, исправьте ошибки в форме';
      return;
    }

    // Проверка, что есть что обновлять
    if (newUsername === username && newEmail === email && !newPassword) {
      error = 'Нет данных для обновления';
      return;
    }

    // Подготовка данных для обновления
    const userData = {};
    if (newUsername !== username) userData.username = newUsername;
    if (newEmail !== email) userData.email = newEmail;
    if (newPassword) userData.password = newPassword;
    if (currentPassword) userData.currentPassword = currentPassword;

    // Обновление данных пользователя
    loading = true;
    try {
      // Choose API method based on context - admin or regular user
      if (adminMode || (currentUser && isAdmin(currentUser) && userId !== currentUser.id)) {
        // Admin updating another user
        await api.admin.updateUserData(userId, userData);
      } else {
        // User updating own profile - include currentPassword
        await api.users.updateUserProfile(userData);

        // Обновляем данные текущего пользователя
        try {
          await api.users.getCurrentUser(); // Обновит данные через userStore

          // Вызываем перезагрузку профиля
          // Отправляем событие, которое Profile.svelte может перехватить и перезагрузить профиль
          window.dispatchEvent(new CustomEvent('profile-updated'));
        } catch (refreshError) {
          console.error('Не удалось обновить данные пользователя:', refreshError);
        }
      }

      success = 'Данные пользователя успешно обновлены';

      // Отправляем событие обновления
      dispatch('userUpdated', {
        username: newUsername,
        email: newEmail
      });

      // Сбрасываем поля пароля
      newPassword = '';
      confirmPassword = '';
      currentPassword = '';
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  // Функция отмены редактирования
  function cancel() {
    // Сбрасываем поля к исходным значениям
    newUsername = username;
    newEmail = email;
    newPassword = '';
    confirmPassword = '';
    currentPassword = '';
    error = null;
    success = null;
    validationErrors = {};

    // Закрываем форму редактирования
    dispatch('cancel');
  }
</script>

<div class="edit-user-form">
  <h4>Редактирование пользователя</h4>

  {#if error}
    <div class="error-message">
      {error}
    </div>
  {/if}

  {#if success}
    <div class="success-message">
      {success}
    </div>
  {/if}

  <div class="form-group">
    <label for="username">Имя пользователя</label>
    <input
      type="text"
      id="username"
      bind:value={newUsername}
      disabled={loading}
      required
      class:input-error={validationErrors.username}
    />
    {#if validationErrors.username}
      <div class="validation-error">{validationErrors.username}</div>
    {/if}
  </div>

  <div class="form-group">
    <label for="email">Email</label>
    <input
      type="email"
      id="email"
      bind:value={newEmail}
      disabled={loading}
      required
      class:input-error={validationErrors.email}
    />
    {#if validationErrors.email}
      <div class="validation-error">{validationErrors.email}</div>
    {/if}
  </div>

  {#if showCurrentPasswordField}
    <div class="form-group current-password">
      <label for="current-password">Текущий пароль <span class="required">*</span></label>
      <input
        type="password"
        id="current-password"
        bind:value={currentPassword}
        disabled={loading}
        required
        placeholder="Введите текущий пароль для подтверждения изменений"
        class:input-error={validationErrors.currentPassword}
      />
      {#if validationErrors.currentPassword}
        <div class="validation-error">{validationErrors.currentPassword}</div>
      {/if}
      <div class="password-info">
        Для безопасности, при изменении личных данных или пароля требуется ввести текущий пароль
      </div>
    </div>
  {/if}

  <div class="form-group">
    <label for="password">Новый пароль</label>
    <input
      type="password"
      id="password"
      bind:value={newPassword}
      disabled={loading}
      placeholder="Оставьте пустым, чтобы не менять"
      class:input-error={validationErrors.password}
    />
    {#if validationErrors.password}
      <div class="validation-error">{validationErrors.password}</div>
    {/if}
  </div>

  <div class="form-group">
    <label for="confirm-password">Подтверждение пароля</label>
    <input
      type="password"
      id="confirm-password"
      bind:value={confirmPassword}
      disabled={loading}
      placeholder="Подтвердите новый пароль"
      class:input-error={validationErrors.confirmPassword}
    />
    {#if validationErrors.confirmPassword}
      <div class="validation-error">{validationErrors.confirmPassword}</div>
    {/if}
  </div>

  <div class="form-actions">
    <button
      type="button"
      class="btn-cancel"
      on:click={cancel}
      disabled={loading}
    >
      Отмена
    </button>
    <button
      type="button"
      class="btn-save"
      on:click={saveChanges}
      disabled={loading}
    >
      {loading ? 'Сохранение...' : 'Сохранить изменения'}
    </button>
  </div>
</div>

<style>
  .edit-user-form {
    max-width: 500px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f8f9fa;
    border-radius: 5px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  h4 {
    margin-top: 0;
    margin-bottom: 20px;
    color: #333;
  }

  .error-message {
    padding: 10px;
    background-color: #f8d7da;
    color: #721c24;
    border-radius: 4px;
    margin-bottom: 15px;
  }

  .success-message {
    padding: 10px;
    background-color: #d4edda;
    color: #155724;
    border-radius: 4px;
    margin-bottom: 15px;
  }

  .form-group {
    margin-bottom: 15px;
  }

  label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
    color: #495057;
  }

  input {
    width: 100%;
    padding: 10px;
    font-size: 16px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    box-sizing: border-box;
  }

  input:focus {
    border-color: #80bdff;
    outline: 0;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
  }

  .input-error {
    border-color: #dc3545;
  }

  .validation-error {
    color: #dc3545;
    font-size: 0.875rem;
    margin-top: 0.25rem;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
  }

  .btn-cancel,
  .btn-save {
    padding: 10px 15px;
    font-size: 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .btn-cancel {
    background-color: #6c757d;
    color: white;
  }

  .btn-cancel:hover {
    background-color: #5a6268;
  }

  .btn-save {
    background-color: #007bff;
    color: white;
  }

  .btn-save:hover {
    background-color: #0069d9;
  }

  .btn-cancel:disabled,
  .btn-save:disabled {
    background-color: #b3b7bb;
    cursor: not-allowed;
  }

  .current-password {
    border-top: 1px dashed #ccc;
    border-bottom: 1px dashed #ccc;
    padding: 15px 0;
    margin: 15px 0;
    background-color: #f0f4f8;
    padding: 15px;
    border-radius: 4px;
  }

  .required {
    color: #dc3545;
  }

  .password-info {
    font-size: 0.8rem;
    color: #6c757d;
    margin-top: 5px;
    font-style: italic;
  }
</style>