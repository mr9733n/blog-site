<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { api } from "../stores/userStore";

  let posts = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      posts = await api.getPosts();
      loading = false;
    } catch (err) {
      error = err.message;
      loading = false;
    }
  });

  // Функция для форматирования даты
  function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('ru', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }

  // Функция для обрезки длинного контента
  function truncateContent(content, maxLength = 300) {
    if (content.length <= maxLength) return content;
    const truncated = content.substr(0, maxLength);
    // Try to end at a space to avoid cutting words
    const lastSpace = truncated.lastIndexOf(' ');
    return truncated.substr(0, lastSpace > maxLength - 20 ? lastSpace : maxLength) + '...';
  }
</script>

<div class="home">
  <h1>Последние записи блога</h1>

  {#if loading}
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>Загрузка постов...</p>
    </div>
  {:else if error}
    <div class="alert alert-danger">
      <p>Ошибка: {error}</p>
    </div>
  {:else if posts.length === 0}
    <div class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
        <polyline points="10 9 9 9 8 9"></polyline>
      </svg>
      <p>Пока нет ни одного поста. Будьте первым, кто напишет!</p>
      <Link to="/create" class="btn btn-primary">Создать пост</Link>
    </div>
  {:else}
    <div class="posts-list">
      {#each posts as post}
        <article class="post-card">
          <header>
            <h2 class="post-title">
              <Link to={`/post/${post.id}`}>{post.title}</Link>
            </h2>
            <div class="post-meta">
              <span class="post-author">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                {post.username}
              </span>
              <span class="post-date">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                {formatDate(post.created_at)}
              </span>
            </div>
          </header>

          <div class="post-content">
            {truncateContent(post.content)}
          </div>

          <footer>
            <Link to={`/post/${post.id}`} class="read-more">
              Читать дальше
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </Link>
          </footer>
        </article>
      {/each}
    </div>
  {/if}
</div>

<style>
  .home {
    max-width: 800px;
    margin: 0 auto;
    padding: 0 1rem;
  }

  h1 {
    margin-bottom: 2rem;
    text-align: center;
    color: var(--text-primary);
    font-size: 2rem;
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    background-color: var(--bg-secondary);
    border-radius: 5px;
    box-shadow: var(--card-shadow);
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--border-color);
    border-top: 4px solid var(--accent-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    background-color: var(--bg-secondary);
    border-radius: 5px;
    box-shadow: var(--card-shadow);
    color: var(--text-secondary);
    text-align: center;
  }

  .empty-state svg {
    margin-bottom: 1rem;
    color: var(--text-secondary);
  }

  .empty-state p {
    margin-bottom: 1.5rem;
    font-size: 1.1rem;
  }

  .posts-list {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .post-card {
    background-color: var(--bg-secondary);
    border-radius: 5px;
    box-shadow: var(--card-shadow);
    padding: 1.5rem;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    display: flex;
    flex-direction: column;
  }

  .post-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
  }

  .post-title {
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.6rem;
  }

  .post-title :global(a) {
    color: var(--text-primary);
    text-decoration: none;
    transition: color 0.2s;
  }

  .post-title :global(a:hover) {
    color: var(--accent-color);
  }

  .post-meta {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  .post-author, .post-date {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .post-content {
    color: var(--text-primary);
    line-height: 1.7;
    margin-bottom: 1.5rem;
    flex-grow: 1;
  }

  footer {
    display: flex;
    justify-content: flex-end;
    border-top: 1px solid var(--border-color);
    padding-top: 1rem;
    margin-top: 0.5rem;
  }

  .read-more {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--accent-color);
    font-weight: 500;
    text-decoration: none;
    transition: color 0.2s;
  }

  .read-more:hover {
    color: var(--accent-hover);
  }

  @media (max-width: 768px) {
    .post-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.5rem;
    }
  }
</style>