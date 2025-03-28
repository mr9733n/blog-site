import App from './App.svelte';
import { updateUserActivity } from './stores/userStore';
import './global.css';

// Глобальное отслеживание активности пользователя
window.addEventListener('click', updateUserActivity);
window.addEventListener('keypress', updateUserActivity);

const app = new App({
  target: document.body,
  props: {
    // можно передать URL для маршрутизатора
    url: window.location.pathname
  }
});

export default app;