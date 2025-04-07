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
  import { updateUserActivity, userStore } from './stores/userStore';
  import { checkTokenExpiration, logout } from './stores/authService';
  import { isAdmin } from "./utils/authWrapper";
  import { onMount } from "svelte";

  export let url = "";
  let user;
  let menuOpen = false;
  let darkMode = false;

  userStore.subscribe(value => {
    user = value;
  });

  function toggleDarkMode() {
    darkMode = !darkMode;
    document.body.classList.toggle('dark-mode', darkMode);
  }

  // Update activity on app load
onMount(() => {
  // Add event listeners for activity tracking
  window.addEventListener('click', updateUserActivity);
  window.addEventListener('keypress', updateUserActivity);
  window.addEventListener('touchstart', updateUserActivity);

  // Prevent auth check loops by using sessionStorage flag
  const isAuthCheck = sessionStorage.getItem('auth_check_in_progress');

  if (!isAuthCheck) {
    // Set flag to prevent multiple simultaneous checks
    sessionStorage.setItem('auth_check_in_progress', 'true');

    console.log("App.svelte: Checking token expiration");

    // Check token on mount (only once)
    const tokenValid = checkTokenExpiration();

    if (!tokenValid) {
      console.log("App.svelte: Token invalid, logging out");
      logout();
      // Note: Don't navigate here - let the router handle it
    }

    // Clear auth check flag
    setTimeout(() => {
      sessionStorage.removeItem('auth_check_in_progress');
    }, 1000);
  } else {
    console.log("App.svelte: Auth check already in progress, skipping");
  }

  // Initialize dark mode from preferences if available
  const savedDarkMode = localStorage.getItem('darkMode');
  if (savedDarkMode) {
    darkMode = savedDarkMode === 'true';
    document.body.classList.toggle('dark-mode', darkMode);
  }
});

  // Handle link clicks
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
  <ImageViewer />

  <nav>
    <div class="container nav-container">
      <div class="nav-left">
        <div class="brand">
          <Link to="/" on:click={handleLinkClick}>My Blog</Link>
        </div>
      </div>

      <button class="menu-toggle" on:click={toggleMenu} aria-label="Toggle menu">
        ☰
      </button>

      <div class="nav-right">
        <ul class="nav-links {menuOpen ? 'open' : ''}">
          <li><Link to="/" on:click={handleLinkClick}>Home</Link></li>
          {#if user}
            <li><Link to="/create" on:click={handleLinkClick}>New Post</Link></li>
            <li><Link to="/profile" on:click={handleLinkClick}>Profile</Link></li>
            <li><button on:click={() => { handleLogout(); handleLinkClick(); }}>Logout</button></li>
          {:else}
            <li><Link to="/login" on:click={handleLinkClick}>Login</Link></li>
          {/if}
        </ul>
        <ThemeToggle on:toggle={toggleDarkMode} />
      </div>
    </div>
  </nav>

  <main>
    <div class="container">
      <Route path="/" component={Home} />
      <Route path="/login" component={Login} />
      <Route path="/register" component={Register} />
      <Route path="/post/:id" component={BlogPost} />
      <Route path="/profile" component={AuthGuard} childComponent={Profile} />
      <Route path="/create" component={AuthGuard} childComponent={CreatePost} />
      <Route path="/edit/:id" component={AuthGuard} childComponent={EditPost} />
    </div>
  </main>

  <footer>
    <div class="container">
      <p>&copy; 2025 My Blog. All rights reserved.</p>
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