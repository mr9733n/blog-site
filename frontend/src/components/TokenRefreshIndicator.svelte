<!-- TokenRefreshIndicator.svelte -->
<script>
  import { tokenRefreshLoading, tokenExpiration } from '../stores/userStore';
  import { refreshToken } from '../stores/authService';

  // Show warning when token is about to expire
  $: showWarning = $tokenExpiration > 0 && $tokenExpiration < 300; // Show warning when less than 5 minutes left

  // Function to refresh token manually
  async function handleRefresh() {
    await refreshToken();
  }
</script>

{#if $tokenRefreshLoading}
  <div class="token-refresh-indicator loading">
    <div class="spinner"></div>
    <span>Обновление сессии...</span>
  </div>
{:else if showWarning}
  <div class="token-refresh-indicator warning">
    <span>Сессия истекает через {$tokenExpiration} сек.</span>
    <button on:click={handleRefresh} class="refresh-btn">Обновить</button>
  </div>
{/if}

<style>
  .token-refresh-indicator {
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 10px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    animation: fadeIn 0.3s;
  }

  .loading {
    background-color: #fff;
  }

  .warning {
    background-color: #fff3cd;
    color: #856404;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .refresh-btn {
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 0.9rem;
    cursor: pointer;
  }

  .refresh-btn:hover {
    background-color: #0069d9;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>