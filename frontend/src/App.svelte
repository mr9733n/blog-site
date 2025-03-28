<script>
  import { Router, Route, Link, navigate } from "svelte-routing";
  import TokenRefreshIndicator from './components/TokenRefreshIndicator.svelte';
  import ThemeToggle from './components/ThemeToggle.svelte';
  import ImageViewer from './components/ImageViewer.svelte';
  import Home from "./components/Home.svelte";
  import Login from "./components/Login.svelte";
  import Register from "./components/Register.svelte";
  import BlogPost from "./components/BlogPost.svelte";
  import CreatePost from "./components/CreatePost.svelte";
  import EditPost from "./components/EditPost.svelte";
  import Profile from "./components/Profile.svelte";
  import AuthGuard from "./components/AuthGuard.svelte";
  import { userStore, updateUserActivity, logout } from './stores/userStore';
  import { onMount } from "svelte";

  export let url = "";
  let user;
  let menuOpen = false;

  userStore.subscribe(value => {
    user = value;
  });

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
    if (menuOpen) toggleMenu();
  }

  function handleLogout() {
    logout();
    navigate("/", { replace: true });
  }

  function toggleMenu() {
    menuOpen = !menuOpen;
  }
</script>

<Router {url}>
  <TokenRefreshIndicator />
  <ImageViewer /> <!-- Добавляем компонент просмотра изображений -->

  <nav>
    <div class="container nav-container">
      <div class="nav-left">
        <div class="brand">
          <Link to="/" on:click={handleLinkClick}>Мой Блог</Link>
        </div>
      </div>

      <button class="menu-toggle" on:click={toggleMenu} aria-label="Toggle menu">
        ☰
      </button>

      <div class="nav-right">
        <ul class="nav-links {menuOpen ? 'open' : ''}">
          <li><Link to="/" on:click={handleLinkClick}>Главная</Link></li>
          {#if user}
            <li><Link to="/create" on:click={handleLinkClick}>Новый пост</Link></li>
            <li><Link to="/profile" on:click={handleLinkClick}>Профиль</Link></li>
            <li><button on:click={() => { handleLogout(); handleLinkClick(); }}>Выйти</button></li>
          {:else}
            <li><Link to="/login" on:click={handleLinkClick}>Войти</Link></li>
            <li><Link to="/register" on:click={handleLinkClick}>Регистрация</Link></li>
          {/if}
        </ul>
        <ThemeToggle />
      </div>
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
  nav {
    background-color: var(--nav-bg);
    color: var(--nav-text);
    padding: 1rem 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    position: sticky;
    top: 0;
    z-index: 1000;
  }

  .nav-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .nav-left, .nav-right {
    display: flex;
    align-items: center;
  }

  .brand {
    font-size: 1.5rem;
    font-weight: bold;
  }

  .brand :global(a) {
    color: var(--nav-text);
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

  .nav-links :global(a), .nav-links button {
    color: var(--nav-text);
    text-decoration: none;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s;
    font-size: 0.9rem;
  }

  .nav-links :global(a:hover), .nav-links button:hover {
    background-color: rgba(255, 255, 255, 0.1);
    text-decoration: none;
  }

  button {
    background: none;
    border: none;
    color: var(--nav-text);
    cursor: pointer;
    font-size: 1rem;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  main {
    min-height: calc(100vh - 140px);
    padding: 2rem 0;
  }

  footer {
    background-color: var(--nav-bg);
    color: var(--nav-text);
    padding: 1rem 0;
    text-align: center;
    margin-top: 2rem;
  }

  footer p {
    margin: 0;
    font-size: 0.9rem;
    opacity: 0.8;
  }

  .menu-toggle {
    display: none;
  }

  @media (max-width: 768px) {
    .nav-links {
      flex-direction: column;
      position: absolute;
      top: 60px;
      right: 0;
      left: 0;
      background-color: var(--nav-bg);
      border-radius: 0 0 4px 4px;
      padding: 1rem;
      gap: 1rem;
      display: none;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      z-index: 100;
    }

    .nav-links.open {
      display: flex;
    }

    .menu-toggle {
      display: block;
      font-size: 1.5rem;
    }

    .nav-right {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
  }
</style>