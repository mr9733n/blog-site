<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { api } from "../stores/apiService";
  import { renderMarkdown } from "../utils/markdown";

  let posts = [];
  let loading = true;
  let error = null;
  let mountCount = 0;
  let isLoading = true;
  let hasFetchedPosts = false;

onMount(() => {
  mountCount++;
  console.log(`Home component mounted ${mountCount} times`);

  if (!hasFetchedPosts) {
    hasFetchedPosts = true;
    fetchPosts();
  } else {
    console.log("Posts already fetched, skipping redundant fetch");
  }

  // Return a cleanup function
  return () => {
    console.log("Home component unmounted");
  };
});

async function fetchPosts() {
  console.log("fetchPosts called at", new Date().toISOString());
  try {
    posts = await api.getPosts();
    console.log(`Received ${posts.length} posts`);
    loading = false;
  } catch (err) {
    error = err.message;
    loading = false;
  }
}

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

  // Функция для обрезки длинного контента и рендеринга markdown
  function truncateAndRenderContent(content, maxLength = 500) {
    // Check if content includes image markdown
    const firstImageMatch = content.match(/!\[([^\]]+)\]\(([^)]+)\)/);

    // First extract the thumbnail image if any
    let thumbnailImage = null;
    if (firstImageMatch) {
      thumbnailImage = {
        alt: firstImageMatch[1],
        url: firstImageMatch[2]
      };
    }

    // Then truncate the content and remove the first image from it
    let truncatedContent = content;

    // Remove first image from content to avoid duplication
    if (firstImageMatch) {
      truncatedContent = truncatedContent.replace(firstImageMatch[0], '');
    }

    // Truncate content if it's too long
    if (truncatedContent.length > maxLength) {
      truncatedContent = truncatedContent.substr(0, maxLength);
      // Try to end at a space to avoid cutting words
      const lastSpace = truncatedContent.lastIndexOf(' ');
      truncatedContent = truncatedContent.substr(0, lastSpace > maxLength - 20 ? lastSpace : maxLength) + '...';
    }

    // Render the truncated content as markdown
    return {
      thumbnailImage,
      renderedContent: renderMarkdown(truncatedContent)
    };
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
        <!-- Process content for each post -->
        {@const { thumbnailImage, renderedContent } = truncateAndRenderContent(post.content)}

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

          <!-- Display thumbnail image if available -->
          {#if thumbnailImage}
            <div class="post-thumbnail">
              <Link to={`/post/${post.id}`}>
                <img src={thumbnailImage.url} alt={thumbnailImage.alt} />
              </Link>
            </div>
          {/if}

          <!-- Only show content if there is some after removing the image -->
          {#if renderedContent && renderedContent.trim() !== ''}
            <div class="post-content markdown-content">
              {@html renderedContent}
            </div>
          {/if}

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

  .post-thumbnail {
    margin-bottom: 1.5rem;
    border-radius: 5px;
    overflow: hidden;
    max-height: 300px;
  }

  .post-thumbnail img {
    width: 100%;
    height: auto;
    object-fit: cover;
    transition: transform 0.3s ease;
  }

  .post-card:hover .post-thumbnail img {
    transform: scale(1.02);
  }

  .post-content {
    color: var(--text-primary);
    line-height: 1.7;
    margin-bottom: 1.5rem;
    flex-grow: 1;
  }

  /* Styles for markdown content */
  :global(.markdown-content h1) {
    font-size: 1.8rem;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 0.5rem;
  }

  :global(.markdown-content h2) {
    font-size: 1.6rem;
    margin-top: 1.4rem;
    margin-bottom: 0.9rem;
  }

  :global(.markdown-content h3) {
    font-size: 1.4rem;
    margin-top: 1.3rem;
    margin-bottom: 0.8rem;
  }

  :global(.markdown-content p) {
    margin-bottom: 1rem;
  }

  :global(.markdown-content img) {
    max-width: 100%;
    height: auto;
    border-radius: 5px;
    margin: 1rem 0;
  }

  footer {
    display: flex;
    justify-content: flex-end;
    border-top: 1px solid var(--border-color);
    padding-top: 1rem;
    margin-top: 0.5rem;
  }

  @media (max-width: 768px) {
    .post-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.5rem;
    }
  }
</style>