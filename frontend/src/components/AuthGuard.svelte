<!-- AuthGuard.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { userStore } from '../stores/userStore';
  import { authFetch } from '../stores/authService';

  export let childComponent; // Component to render when authenticated
  export let id = undefined;

  let user;
  let loading = true;
  let authenticated = false;

  // Subscribe to user store
  userStore.subscribe(value => {
    user = value;
  });

  onMount(async () => {
    // Use authFetch to check authentication AND trigger token refresh if needed
    try {
      loading = true;

      // Try to fetch the current user info to verify auth
      await authFetch('/api/me');

      // If we get here, the user is authenticated
      authenticated = true;
    } catch (err) {
      console.warn('Authentication failed in AuthGuard:', err.message);
      authenticated = false;
      navigate('/login', { replace: true });
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="auth-loading">
    <div class="spinner"></div>
    <p>Проверка аутентификации...</p>
  </div>
{:else if authenticated && user}
  <svelte:component this={childComponent} {id} />
{:else}
  <div class="redirect-message">
    <div class="spinner"></div>
    <p>Перенаправление на страницу входа...</p>
  </div>
{/if}

<style>
  .auth-loading, .redirect-message {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    background-color: #f8f9fa;
    border-radius: 5px;
    text-align: center;
    margin: 2rem auto;
    max-width: 400px;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
</style>