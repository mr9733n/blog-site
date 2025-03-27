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
  function truncateContent(content, maxLength = 150) {
    if (content.length <= maxLength) return content;
    return content.substr(0, maxLength) + '...';
  }
</script>

<div class="home">
  <h1>Последние записи блога</h1>

  {#if loading}
    <div class="loading">Загрузка постов...</div>
  {:else if error}
    <div class="error">Ошибка: {error}</div>
  {:else if posts.length === 0}
    <div class="empty">Пока нет ни одного поста. Будьте первым, кто напишет!</div>
  {:else}
    <div class="posts-grid">
      {#each posts as post}
        <div class="post-card">
          <h2 class="post-title">
            <Link to={`/post/${post.id}`}>{post.title}</Link>
          </h2>
          <div class="post-meta">
            <span class="post-author">Автор: {post.username}</span>
            <span class="post-date">Опубликовано: {formatDate(post.created_at)}</span>
          </div>
          <div class="post-content">
            {truncateContent(post.content)}
          </div>
          <div class="post-read-more">
            <Link to={`/post/${post.id}`}>Читать дальше →</Link>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .home {
    margin-bottom: 2rem;
  }

  h1 {
    margin-bottom: 2rem;
    text-align: center;
    color: #333;
  }

  .loading, .error, .empty {
    text-align: center;
    padding: 2rem;
    background-color: #f8f9fa;
    border-radius: 5px;
  }

  .error {
    color: #721c24;
    background-color: #f8d7da;
  }

  .posts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 2rem;
  }

  .post-card {
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 1.5rem;
    transition: transform 0.3s ease;
    display: flex;
    flex-direction: column;
  }

  .post-card:hover {
    transform: translateY(-5px);
  }

  .post-title {
    margin-top: 0;
    margin-bottom: 1rem;
  }

  .post-title :global(a) {
    color: #333;
    text-decoration: none;
  }

  .post-title :global(a:hover) {
    color: #007bff;
  }

  .post-meta {
    display: flex;
    flex-direction: column;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: #6c757d;
  }

  .post-content {
    flex-grow: 1;
    margin-bottom: 1rem;
    color: #495057;
    line-height: 1.5;
  }

  .post-read-more {
    text-align: right;
  }

  .post-read-more :global(a) {
    color: #007bff;
    text-decoration: none;
  }

  .post-read-more :global(a:hover) {
    text-decoration: underline;
  }
</style>