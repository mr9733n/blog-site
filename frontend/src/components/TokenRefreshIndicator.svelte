<!-- TokenRefreshIndicator.svelte -->
<script>
  import { tokenRefreshLoading } from '../stores/userStore';
</script>

{#if $tokenRefreshLoading}
  <div class="token-refresh-indicator">
    <div class="spinner"></div>
    <span>Обновление сессии...</span>
  </div>
{/if}

<style>
  .token-refresh-indicator {
    position: fixed;
    top: 10px;
    right: 10px;
    background-color: #fff;
    padding: 10px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    z-index: 1000;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
</style>