<!-- UserSettings.svelte -->
<script>
  import { onMount } from 'svelte';
  import { api, userStore } from '../stores/userStore';

  let tokenLifetime = 1800; // Default 30 minutes
  let saving = false;
  let success = false;
  let error = null;

  onMount(async () => {
    // Get current token lifetime from localStorage
    const savedLifetime = localStorage.getItem('tokenLifetime');
    if (savedLifetime) {
      tokenLifetime = parseInt(savedLifetime);
    }
  });

  async function saveSettings() {
    saving = true;
    error = null;
    success = false;

    try {
      await api.updateTokenLifetime(tokenLifetime);
      localStorage.setItem('tokenLifetime', tokenLifetime.toString());
      success = true;

      // Auto-hide success message after 3 seconds
      setTimeout(() => {
        success = false;
      }, 3000);
    } catch (err) {
      error = err.message;
    } finally {
      saving = false;
    }
  }

  function formatLifetime(seconds) {
    if (seconds < 3600) {
      return `${Math.round(seconds / 60)} минут`;
    } else {
      return `${Math.round(seconds / 3600 * 10) / 10} часов`;
    }
  }
</script>

<div class="settings-container">
  <h3>Настройки безопасности</h3>

  <div class="setting-group">
    <label for="token-lifetime">Время жизни сессии: <span class="lifetime-value">{formatLifetime(tokenLifetime)}</span></label>
    <div class="range-container">
      <span class="range-label">5 мин</span>
      <input
        type="range"
        id="token-lifetime"
        min="300"
        max="86400"
        step="300"
        bind:value={tokenLifetime}
        class="slider"
      />
      <span class="range-label">24 ч</span>
    </div>
    <p class="setting-description">
      Это время, в течение которого вы остаетесь авторизованными без необходимости повторного входа.
      Более короткий период повышает безопасность, более длинный - удобство использования.
    </p>
  </div>

  <div class="button-container">
    <button class="save-button" on:click={saveSettings} disabled={saving}>
      {saving ? 'Сохранение...' : 'Сохранить настройки'}
    </button>
  </div>

  {#if success}
    <div class="alert success">
      <span class="alert-icon">✓</span>
      Настройки успешно сохранены
    </div>
  {/if}

  {#if error}
    <div class="alert error">
      <span class="alert-icon">!</span>
      {error}
    </div>
  {/if}
</div>

<style>
  .settings-container {
    background-color: #fff;
    border-radius: 6px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  h3 {
    font-size: 1.25rem;
    color: #333;
    margin-top: 0;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
  }

  .setting-group {
    margin-bottom: 24px;
  }

  label {
    display: block;
    font-weight: 600;
    margin-bottom: 10px;
    color: #495057;
  }

  .lifetime-value {
    font-weight: 700;
    color: #007bff;
  }

  .range-container {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
  }

  .range-label {
    color: #6c757d;
    font-size: 0.85rem;
    width: 40px;
  }

  .slider {
    flex: 1;
    height: 6px;
    -webkit-appearance: none;
    appearance: none;
    background: #dee2e6;
    outline: none;
    border-radius: 3px;
    margin: 0 10px;
  }

  .slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    background: #007bff;
    border-radius: 50%;
    cursor: pointer;
    transition: background 0.2s;
  }

  .slider::-moz-range-thumb {
    width: 18px;
    height: 18px;
    background: #007bff;
    border-radius: 50%;
    cursor: pointer;
    transition: background 0.2s;
    border: none;
  }

  .slider::-webkit-slider-thumb:hover {
    background: #0056b3;
  }

  .slider::-moz-range-thumb:hover {
    background: #0056b3;
  }

  .setting-description {
    font-size: 0.9rem;
    color: #6c757d;
    margin-top: 8px;
    line-height: 1.4;
  }

  .button-container {
    margin-top: 24px;
  }

  .save-button {
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 10px 16px;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .save-button:hover:not(:disabled) {
    background-color: #0069d9;
  }

  .save-button:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
    opacity: 0.65;
  }

  .alert {
    margin-top: 16px;
    padding: 12px 16px;
    border-radius: 4px;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    animation: fadeIn 0.3s ease-in-out;
  }

  .alert.success {
    background-color: #d4edda;
    color: #155724;
    border-left: 4px solid #28a745;
  }

  .alert.error {
    background-color: #f8d7da;
    color: #721c24;
    border-left: 4px solid #dc3545;
  }

  .alert-icon {
    font-weight: bold;
    margin-right: 10px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    text-align: center;
  }

  .success .alert-icon {
    background-color: #28a745;
    color: white;
  }

  .error .alert-icon {
    background-color: #dc3545;
    color: white;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>