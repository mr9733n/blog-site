<!-- EditUser.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { api } from "../stores/userStore";

  export let userId;
  export let username;
  export let email;

  let newUsername = username;
  let newEmail = email;
  let newPassword = '';
  let confirmPassword = '';
  let error = null;
  let success = null;
  let loading = false;

  const dispatch = createEventDispatcher();

  // Функция сохранения изменений
  async function saveChanges() {
    // Очистка предыдущих сообщений
    error = null;
    success = null;

    // Проверка, что пароли совпадают, если они заполнены
    if (newPassword && newPassword !== confirmPassword) {
      error = 'Пароли не совпадают';
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

    // Обновление данных пользователя
    loading = true;
    try {
      await api.updateUserData(userId, userData);
      success = 'Данные пользователя успешно обновлены';

      // Отправляем событие обновления
      dispatch('userUpdated', {
        username: newUsername,
        email: newEmail
      });

      // Сбрасываем поля пароля
      newPassword = '';
      confirmPassword = '';
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
    error = null;
    success = null;

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
    />
  </div>

  <div class="form-group">
    <label for="email">Email</label>
    <input
      type="email"
      id="email"
      bind:value={newEmail}
      disabled={loading}
      required
    />
  </div>

  <div class="form-group">
    <label for="password">Новый пароль</label>
    <input
      type="password"
      id="password"
      bind:value={newPassword}
      disabled={loading}
      placeholder="Оставьте пустым, чтобы не менять"
    />
  </div>

  <div class="form-group">
    <label for="confirm-password">Подтверждение пароля</label>
    <input
      type="password"
      id="confirm-password"
      bind:value={confirmPassword}
      disabled={loading}
      placeholder="Подтвердите новый пароль"
    />
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
</style>