<script>
  import { onMount } from 'svelte';
  import { api, userStore } from "../stores/userStore";

  let tokenLifetime = 1800; // 30 минут по умолчанию
  let refreshTokenLifetime = 1296000; // 15 дней по умолчанию
  let loading = false;
  let success = false;
  let error = null;
  let user = null;

  userStore.subscribe(value => {
    user = value;
  });

  onMount(async () => {
    // Загружаем текущее значение из локального хранилища
    const storedTokenLifetime = localStorage.getItem('tokenLifetime');
    if (storedTokenLifetime) {
      tokenLifetime = parseInt(storedTokenLifetime);
    }

    // В будущем можно также загружать из API, если мы сохраняем эти значения в БД
  });

  async function updateSettings() {
    if (!user) return;

    loading = true;
    success = false;
    error = null;

    try {
      // Валидация значений
      if (tokenLifetime < 300 || tokenLifetime > 86400) {
        throw new Error('Время жизни токена должно быть от 5 минут до 24 часов');
      }

      if (refreshTokenLifetime < 86400 || refreshTokenLifetime > 2592000) {
        throw new Error('Время жизни refresh токена должно быть от 1 до 30 дней');
      }

      // Отправка запроса на обновление настроек
      const response = await api.updateTokenSettings(tokenLifetime, refreshTokenLifetime);
      success = true;

      // Обновляем значение в локальном хранилище
      localStorage.setItem('tokenLifetime', tokenLifetime.toString());

    } catch (err) {
      error = err.message;
    } finally {
      loading = false;

      // Автоматически скрываем сообщение об успехе через 3 секунды
      if (success) {
        setTimeout(() => {
          success = false;
        }, 3000);
      }
    }
  }
</script>

<div class="settings-container">
  <h2>Настройки безопасности</h2>

  {#if success}
    <div class="success-message">
      Настройки успешно обновлены
    </div>
  {/if}

  {#if error}
    <div class="error-message">
      {error}
    </div>
  {/if}

  <div class="settings-form">
    <div class="form-group">
      <label for="tokenLifetime">Время жизни токена доступа (в секундах)</label>
      <div class="input-with-help">
        <input
          type="number"
          id="tokenLifetime"
          bind:value={tokenLifetime}
          min="300"
          max="86400"
          disabled={loading}
        />
        <div class="input-help">
          От 5 минут (300) до 24 часов (86400)
        </div>
      </div>
    </div>

    <div class="form-group">
      <label for="refreshTokenLifetime">Время жизни токена обновления (в секундах)</label>
      <div class="input-with-help">
        <input
          type="number"
          id="refreshTokenLifetime"
          bind:value={refreshTokenLifetime}
          min="86400"
          max="2592000"
          disabled={loading}
        />
        <div class="input-help">
          От 1 дня (86400) до 30 дней (2592000)
        </div>
      </div>
    </div>

    <div class="token-presets">
      <div class="preset-title">Быстрый выбор для токена доступа:</div>
      <div class="preset-buttons">
        <button class="preset-btn" on:click={() => tokenLifetime = 300} disabled={loading}>5 минут</button>
        <button class="preset-btn" on:click={() => tokenLifetime = 1800} disabled={loading}>30 минут</button>
        <button class="preset-btn" on:click={() => tokenLifetime = 3600} disabled={loading}>1 час</button>
        <button class="preset-btn" on:click={() => tokenLifetime = 43200} disabled={loading}>12 часов</button>
        <button class="preset-btn" on:click={() => tokenLifetime = 86400} disabled={loading}>24 часа</button>
      </div>
    </div>

    <div class="form-actions">
      <button
        class="save-btn"
        on:click={updateSettings}
        disabled={loading}
      >
        {loading ? 'Сохранение...' : 'Сохранить настройки'}
      </button>
    </div>
  </div>

  <div class="settings-info">
    <h3>Информация о настройках</h3>
    <p>
      <strong>Токен доступа</strong> используется для аутентификации ваших запросов к API.
      Более короткое время жизни повышает безопасность, но потребует более частого входа в систему.
    </p>
    <p>
      <strong>Токен обновления</strong> позволяет автоматически получать новые токены доступа без необходимости повторного входа.
      Более длительное время жизни удобнее, но менее безопасно.
    </p>
  </div>
</div>

<style>
  .settings-container {
    background-color: #fff;
    border-radius: 5px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  h2 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    color: #333;
    font-size: 1.5rem;
  }

  .success-message {
    background-color: #d4edda;
    color: #155724;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border-radius: 4px;
  }

  .error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border-radius: 4px;
  }

  .settings-form {
    margin-bottom: 2rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
    color: #333;
  }

  .input-with-help {
    position: relative;
  }

  input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 1rem;
  }

  input:focus {
    outline: none;
    border-color: #80bdff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
  }

  .input-help {
    margin-top: 0.25rem;
    font-size: 0.875rem;
    color: #6c757d;
  }

  .token-presets {
    margin-bottom: 1.5rem;
  }

  .preset-title {
    margin-bottom: 0.5rem;
    font-weight: bold;
  }

  .preset-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .preset-btn {
    background-color: #e9ecef;
    border: none;
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: background-color 0.2s;
  }

  .preset-btn:hover {
    background-color: #dee2e6;
  }

  .form-actions {
    margin-top: 2rem;
  }

  .save-btn {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.2s;
  }

  .save-btn:hover:not(:disabled) {
    background-color: #0069d9;
  }

  .save-btn:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
  }

  .settings-info {
    background-color: #f8f9fa;
    padding: 1.5rem;
    border-radius: 4px;
  }

  .settings-info h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.25rem;
    color: #333;
  }

  .settings-info p {
    margin-bottom: 0.75rem;
    font-size: 0.95rem;
    line-height: 1.5;
    color: #495057;
  }
</style>