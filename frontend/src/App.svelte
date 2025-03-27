<script>
  import { Router, Route, Link } from "svelte-routing";
  import Home from "./components/Home.svelte";
  import Login from "./components/Login.svelte";
  import Register from "./components/Register.svelte";
  import BlogPost from "./components/BlogPost.svelte";
  import CreatePost from "./components/CreatePost.svelte";
  import EditPost from "./components/EditPost.svelte";
  import Profile from "./components/Profile.svelte";
  import AuthGuard from "./components/AuthGuard.svelte";
  import { userStore } from "./stores/userStore";
  import { updateUserActivity } from './stores/userStore';
  import { onMount } from "svelte";

  export let url = "";
  let user;

  userStore.subscribe(value => {
    user = value;
  });

  function logout() {
    userStore.set(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
  }

  // Обновляем активность при загрузке приложения
  onMount(() => {
    updateUserActivity();

    // Отслеживаем навигацию браузера (кнопки назад/вперед)
    window.addEventListener('popstate', updateUserActivity);

    // Отслеживаем когда пользователь возвращается на вкладку
    window.addEventListener('focus', updateUserActivity);

    return () => {
      window.removeEventListener('popstate', updateUserActivity);
      window.removeEventListener('focus', updateUserActivity);
    };
  });

  // Обработчик для клика по ссылкам
  function handleLinkClick() {
    updateUserActivity();
  }
</script>

<Router {url}>
  <nav>
    <div class="container">
      <div class="brand">
        <Link to="/" on:click={handleLinkClick}>Мой Блог</Link>
      </div>
      <ul class="nav-links">
        <li><Link to="/" on:click={handleLinkClick}>Главная</Link></li>
        {#if user}
          <li><Link to="/create" on:click={handleLinkClick}>Новый пост</Link></li>
          <li><Link to="/profile" on:click={handleLinkClick}>Профиль</Link></li>
          <li><button on:click={logout}>Выйти</button></li>
        {:else}
          <li><Link to="/login" on:click={handleLinkClick}>Войти</Link></li>
          <li><Link to="/register" on:click={handleLinkClick}>Регистрация</Link></li>
        {/if}
      </ul>
    </div>
  </nav>

  <main>
    <div class="container">
      <!-- Публичные маршруты - доступны всем -->
      <Route path="/" component={Home} />
      <Route path="/login" component={Login} />
      <Route path="/register" component={Register} />
      <Route path="/post/:id" let:params>
        <BlogPost id={params.id} />
      </Route>

      <!-- Защищенные маршруты - только для авторизованных пользователей -->
      <AuthGuard>
        <Route path="/create" component={CreatePost} />
        <Route path="/edit/:id" let:params>
          <EditPost id={params.id} />
        </Route>
        <Route path="/profile" component={Profile} />
      </AuthGuard>
    </div>
  </main>

  <footer>
    <div class="container">
      <p>&copy; 2025 Мой Блог. Все права защищены.</p>
    </div>
  </footer>
</Router>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
      Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
    line-height: 1.6;
    background-color: #f8f9fa;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
  }

  nav {
    background-color: #333;
    color: white;
    padding: 1rem 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  nav .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .brand {
    font-size: 1.5rem;
    font-weight: bold;
  }

  .brand :global(a) {
    color: white;
    text-decoration: none;
  }

  .nav-links {
    display: flex;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .nav-links li {
    margin-left: 1rem;
  }

  .nav-links :global(a) {
    color: white;
    text-decoration: none;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .nav-links :global(a:hover) {
    background-color: rgba(255, 255, 255, 0.1);
  }

  button {
    background: none;
    border: none;
    color: white;
    cursor: pointer;
    font-size: 1rem;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  button:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }

  main {
    min-height: calc(100vh - 140px);
    padding: 2rem 0;
  }

  footer {
    background-color: #333;
    color: white;
    padding: 1rem 0;
    text-align: center;
    margin-top: 2rem;
  }

  footer p {
    margin: 0;
    font-size: 0.9rem;
    opacity: 0.8;
  }
</style>