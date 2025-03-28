<script>
  import { onMount, onDestroy } from 'svelte';
  import { Link, navigate } from "svelte-routing";
  import { api, userStore } from "../stores/userStore";
  import UserSettings from './UserSettings.svelte';

  let user = null;
  let userInfo = null;
  let userPosts = [];
  let loading = true;
  let error = null;
  let activeTab = 'posts'; // 'posts', 'saved', or 'settings'
  let tokenExpiresIn = 0;
  let timer;
  let savedPosts = [];

  userStore.subscribe(value => {
    user = value;
  });

  onMount(async () => {
    // Проверка авторизации
    if (!user) {
      navigate("/login", { replace: true });
      return;
    }

    loading = true;

    try {
      // Загрузка информации о текущем пользователе
      userInfo = await api.getCurrentUser();

      // Загрузка постов пользователя
      userPosts = await api.getUserPosts(userInfo.id);

      loading = false;

		updateTokenTime();
		    timer = setInterval(updateTokenTime, 1000);
	    if (user) {
      await loadSavedPosts();
    }

    } catch (err) {
      error = err.message;
      loading = false;
    }
  });

  onDestroy(() => {
  clearInterval(timer);
});

function updateTokenTime() {
  const token = localStorage.getItem('authToken');
  if (!token) return;

  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(window.atob(base64));

    // Вычисляем оставшееся время в секундах
    tokenExpiresIn = Math.max(0, Math.floor(payload.exp - Date.now()/1000));
  } catch (e) {
    console.error('Ошибка проверки токена', e);
    tokenExpiresIn = 0;
  }
}

  async function loadSavedPosts() {
    try {
      savedPosts = await api.getSavedPosts();
    } catch (err) {
      error = err.message;
    }
  }

  async function unsavePost(postId) {
    try {
      await api.unsavePost(postId);
      // Удаляем пост из списка
      savedPosts = savedPosts.filter(post => post.id !== postId);
    } catch (err) {
      error = err.message;
    }
  }

  function setTab(tab) {
    activeTab = tab;
  }

  // Функция для форматирования даты
  function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('ru', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    }).format(date);
  }

    $: if (activeTab === 'saved' && user) {
    loadSavedPosts();
  }
</script>

<div class="profile-page">
  {#if loading}
    <div class="loading">Загрузка профиля...</div>
  {:else if error}
    <div class="error">
      <p>{error}</p>
      <Link to="/">Вернуться на главную</Link>
    </div>
  {:else if userInfo}
    <div class="profile-container">
      <div class="profile-header">
        <h1>Профиль</h1>
        <div class="profile-info">
          <div class="profile-avatar">
            <div class="avatar-placeholder">{userInfo.username.charAt(0).toUpperCase()}</div>
          </div>
          <div class="profile-details">
            <h2>{userInfo.username}</h2>
            <p class="profile-email">{userInfo.email}</p>
            <p class="profile-date">Участник с {formatDate(userInfo.created_at)}</p>
          <div class="token-info">
  			<p>Срок действия токена: <strong>{tokenExpiresIn} сек.</strong></p>
		  </div>
          </div>
        </div>
      </div>

      <div class="profile-tabs">
        <button
          class="tab {activeTab === 'posts' ? 'active' : ''}"
          on:click={() => setTab('posts')}
        >
          Мои посты ({userPosts.length})
        </button>
        <button
          class="tab {activeTab === 'saved' ? 'active' : ''}"
          on:click={() => setTab('saved')}
        >
          Сохраненные
        </button>
        <button
          class="tab {activeTab === 'settings' ? 'active' : ''}"
          on:click={() => setTab('settings')}
        >
          Настройки
        </button>
      </div>

      <div class="profile-content">
        {#if activeTab === 'posts'}
          <div class="tab-panel">
            {#if userPosts.length === 0}
              <div class="empty-posts">
                <p>У вас пока нет опубликованных постов.</p>
                <Link to="/create" class="create-post-btn">Создать пост</Link>
              </div>
            {:else}
              <div class="post-list">
                {#each userPosts as post}
                  <div class="post-item">
                    <div class="post-title">
                      <Link to={`/post/${post.id}`}>{post.title}</Link>
                    </div>
                    <div class="post-meta">
                      <span class="post-date">{formatDate(post.created_at)}</span>
                    </div>
                    <div class="post-actions">
                      <Link to={`/edit/${post.id}`} class="edit-btn">Редактировать</Link>
                      <Link to={`/post/${post.id}`} class="view-btn">Просмотр</Link>
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
{:else if activeTab === 'saved'}
  <div class="tab-panel">
    {#if savedPosts.length === 0}
      <div class="empty-posts">
        <p>У вас пока нет сохранённых постов.</p>
      </div>
    {:else}
      <div class="post-list">
        {#each savedPosts as post}
          <div class="post-item">
            <div class="post-title">
              <Link to={`/post/${post.id}`}>{post.title}</Link>
            </div>
            <div class="post-meta">
              <span class="post-author">Автор: {post.username}</span>
              <span class="post-date">{formatDate(post.created_at)}</span>
            </div>
            <div class="post-actions">
              <Link to={`/post/${post.id}`} class="view-btn">Просмотр</Link>
              <button class="unsave-btn" on:click={() => unsavePost(post.id)}>
                Удалить из сохранённых
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
        {:else if activeTab === 'settings'}
          <div class="tab-panel">
            <UserSettings />
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .profile-page {
    max-width: 800px;
    margin: 0 auto;
    padding: 1rem 0;
  }

  .loading, .error {
    text-align: center;
    padding: 2rem;
    background-color: #f8f9fa;
    border-radius: 5px;
    margin-bottom: 2rem;
  }

  .error {
    color: #721c24;
    background-color: #f8d7da;
  }

  .error a {
    display: inline-block;
    margin-top: 1rem;
    color: #721c24;
    font-weight: bold;
  }

  .profile-container {
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .profile-header {
    padding: 2rem;
    background-color: #f8f9fa;
    border-bottom: 1px solid #dee2e6;
  }

  .profile-header h1 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    color: #495057;
    font-size: 1.5rem;
  }

  .profile-info {
    display: flex;
    align-items: center;
  }

  .profile-avatar {
    margin-right: 1.5rem;
  }

  .avatar-placeholder {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background-color: #007bff;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    font-weight: bold;
  }

  .profile-details h2 {
    margin-top: 0;
    margin-bottom: 0.5rem;
    color: #212529;
    font-size: 1.5rem;
  }

  .profile-email {
    margin: 0 0 0.5rem;
    color: #6c757d;
  }

  .profile-date {
    margin: 0;
    color: #6c757d;
    font-size: 0.9rem;
  }

  .profile-tabs {
    display: flex;
    border-bottom: 1px solid #dee2e6;
  }

  .tab {
    background: none;
    border: none;
    padding: 1rem 1.5rem;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
    font-family: inherit;
    font-size: inherit;
  }

  .tab:hover {
    color: #007bff;
    background-color: #f8f9fa;
  }

  .tab.active {
    color: #007bff;
    border-bottom-color: #007bff;
    font-weight: bold;
  }

  .profile-content {
    padding: 2rem;
  }

  .tab-panel {
    padding: 10px;
    margin-top: 10px;
    background-color: #f9f9f9;
  }

  .empty-posts {
    text-align: center;
    padding: 2rem;
    color: #6c757d;
  }

  .create-post-btn {
    display: inline-block;
    margin-top: 1rem;
    padding: 0.5rem 1rem;
    background-color: #007bff;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .create-post-btn:hover {
    background-color: #0069d9;
  }

  .post-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .post-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background-color: #f8f9fa;
    border-radius: 5px;
    transition: transform 0.2s;
  }

  .post-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .post-title {
    flex: 1;
  }

  .post-title a {
    color: #212529;
    text-decoration: none;
    font-weight: bold;
  }

  .post-title a:hover {
    color: #007bff;
  }

  .post-meta {
    margin: 0 1rem;
    color: #6c757d;
    font-size: 0.9rem;
  }

  .post-actions {
    display: flex;
    gap: 0.5rem;
  }

  .edit-btn, .view-btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.9rem;
    text-decoration: none;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .edit-btn {
    background-color: #17a2b8;
    color: white;
  }

  .edit-btn:hover {
    background-color: #138496;
  }

  .view-btn {
    background-color: #6c757d;
    color: white;
  }

  .view-btn:hover {
    background-color: #5a6268;
  }
</style>