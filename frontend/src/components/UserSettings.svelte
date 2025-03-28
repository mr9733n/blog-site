<script>
  import { onMount } from 'svelte';
  import { api, userStore } from "../stores/userStore";

  let tokenLifetimeMinutes = 30; // 30 минут по умолчанию
  let refreshTokenLifetimeDays = 15; // 15 дней по умолчанию
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
      // Преобразуем секунды в минуты
      tokenLifetimeMinutes = Math.round(parseInt(storedTokenLifetime) / 60);
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
      if (tokenLifetimeMinutes < 5 || tokenLifetimeMinutes > 1440) {
        throw new Error('Время жизни токена должно быть от 5 минут до 24 часов');
      }

      if (refreshTokenLifetimeDays < 1 || refreshTokenLifetimeDays > 30) {
        throw new Error('Время жизни refresh токена должно быть от 1 до 30 дней');
      }

      // Преобразуем минуты и дни в секунды для API
      const tokenLifetimeSeconds = tokenLifetimeMinutes * 60;
      const refreshTokenLifetimeSeconds = refreshTokenLifetimeDays * 86400;

      // Отправка запроса на обновление настроек
      const response = await api.updateTokenSettings(
        tokenLifetimeSeconds,
        refreshTokenLifetimeSeconds
      );

      success = true;

      // Обновляем значение в локальном хранилище
      localStorage.setItem('tokenLifetime', tokenLifetimeSeconds.toString());

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
      <label for="tokenLifetime">Время жизни токена доступа (в минутах)</label>
      <div class="input-with-help">
        <input
          type="number"
          id="tokenLifetime"
          bind:value={tokenLifetimeMinutes}
          min="5"
          max="1440"
          disabled={loading}
        />
        <div class="input-help">
          От 5 минут до 24 часов (1440 минут)
        </div>
      </div>
    </div>

    <div class="token-presets">
      <div class="preset-title">Быстрый выбор для токена доступа:</div>
      <div class="preset-buttons">
        <button class="preset-btn" on:click={() => tokenLifetimeMinutes = 5} disabled={loading}>5 минут</button>
        <button class="preset-btn" on:click={() => tokenLifetimeMinutes = 30} disabled={loading}>30 минут</button>
        <button class="preset-btn" on:click={() => tokenLifetimeMinutes = 60} disabled={loading}>1 час</button>
        <button class="preset-btn" on:click={() => tokenLifetimeMinutes = 720} disabled={loading}>12 часов</button>
        <button class="preset-btn" on:click={() => tokenLifetimeMinutes = 1440} disabled={loading}>24 часа</button>
      </div>
    </div>

    <div class="form-group">
      <label for="refreshTokenLifetime">Время жизни токена обновления (в днях)</label>
      <div class="input-with-help">
        <input
          type="number"
          id="refreshTokenLifetime"
          bind:value={refreshTokenLifetimeDays}
          min="1"
          max="30"
          disabled={loading}
        />
        <div class="input-help">
          От 1 до 30 дней
        </div>
      </div>
    </div>

    <div class="token-presets">
      <div class="preset-title">Быстрый выбор для токена обновления:</div>
      <div class="preset-buttons">
        <button class="preset-btn" on:click={() => refreshTokenLifetimeDays = 1} disabled={loading}>1 день</button>
        <button class="preset-btn" on:click={() => refreshTokenLifetimeDays = 3} disabled={loading}>3 дня</button>
        <button class="preset-btn" on:click={() => refreshTokenLifetimeDays = 7} disabled={loading}>1 неделя</button>
        <button class="preset-btn" on:click={() => refreshTokenLifetimeDays = 15} disabled={loading}>15 дней</button>
        <button class="preset-btn" on:click={() => refreshTokenLifetimeDays = 30} disabled={loading}>30 дней</button>
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