<!-- AuthGuard.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { userStore, isTokenExpired, updateUserActivity } from '../stores/userStore';

  // Интервал проверки токена каждые 10 секунд
  const CHECK_INTERVAL = 10000;
  // Время неактивности в миллисекундах
  const INACTIVITY_THRESHOLD = 30000; // 30 секунд

  let lastActivity = Date.now();
  let timer;
  let user;

  // Подписываемся на хранилище пользователя
  userStore.subscribe(value => {
    user = value;
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
{/if}