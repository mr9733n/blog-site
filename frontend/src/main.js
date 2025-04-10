import App from './App.svelte';
import { updateUserActivity } from './stores/userStore';
import './global.css';

// Global user activity tracking
// Note: App.svelte also sets these, but these serve as a fallback
window.addEventListener('click', updateUserActivity);
window.addEventListener('keypress', updateUserActivity);
window.addEventListener('touchstart', updateUserActivity);

const app = new App({
  target: document.body,
  props: {
    url: window.location.pathname
  }
});

export default app;