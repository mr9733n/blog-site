<!-- AuthGuard.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { userStore, isTokenExpired, updateUserActivity, INACTIVITY_THRESHOLD  } from '../stores/userStore';

  // Интервал проверки токена каждые 10 секунд
  const CHECK_INTERVAL = 10000;

  let lastActivity = Date.now();
  let timer;
  let user;

  // Подписываемся на хранилище пользователя
userStore.subscribe(value => {
  user = value;
  const token = localStorage.getItem('authToken');
  // If user is not authenticated or token is expired, redirect to login
  if (!user || !token || isTokenExpired(token)) {
    navigate('/login', { replace: true });
  }
});

  function checkToken() {
    if (!user) return;

    const token = localStorage.getItem('authToken');
    if (!token || isTokenExpired(token)) {
      // Если токен истек, проверяем активность
      const inactiveTime = Date.now() - lastActivity;
      if (inactiveTime > INACTIVITY_THRESHOLD) {
        console.log(`Пользователь был неактивен ${inactiveTime/1000} секунд, выход`);
        // Выход пользователя
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
        userStore.set(null);
        navigate('/login', { replace: true });
      }
    }
  }

  function updateActivity() {
    lastActivity = Date.now();
    updateUserActivity(); // Обновляем глобальную активность
  }

  onMount(() => {
    // Проверяем авторизацию сразу при монтировании
    if (!user) {
      navigate('/login', { replace: true });
      return;
    }

    // Начинаем проверку токена при монтировании
    timer = setInterval(checkToken, CHECK_INTERVAL);

    // Слушаем события активности пользователя
    window.addEventListener('click', updateActivity);
    window.addEventListener('keypress', updateActivity);
    window.addEventListener('scroll', updateActivity);
    window.addEventListener('mousemove', updateActivity);

    // Обновляем активность при первой загрузке
    updateActivity();
  });

  onDestroy(() => {
    // Очистка интервала и слушателей при размонтировании
    clearInterval(timer);
    window.removeEventListener('click', updateActivity);
    window.removeEventListener('keypress', updateActivity);
    window.removeEventListener('scroll', updateActivity);
    window.removeEventListener('mousemove', updateActivity);
  });
</script>

{#if user}
  <slot></slot>
{:else}
  <div class="redirect-message">
    <div class="spinner"></div>
    <p>Перенаправление на страницу входа...</p>
  </div>
{/if}

<style>
  .redirect-message {
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