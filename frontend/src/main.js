import App from './App.svelte';

const app = new App({
  target: document.body,
  props: {
    // можно передать URL для маршрутизатора
    url: window.location.pathname
  }
});

export default app;