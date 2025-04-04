<script>
  import { onMount, onDestroy } from 'svelte';
  import { Link, navigate } from "svelte-routing";
  import { api, userStore, tokenExpiration } from "../stores/userStore";
  import UserSettings from './UserSettings.svelte';
  import AdminUsers from './AdminUsers.svelte';

  let user = null;
  let userInfo = null;
  let userPosts = [];
  let userImages = [];
  let loading = true;
  let error = null;
  let activeTab = 'posts'; // 'posts', 'saved', 'images', or 'settings'
  let savedPosts = [];
  let imageDeleteLoading = false;
  let allPosts = [];
  let loadingAllPosts = false;

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

      if (user) {
        await loadSavedPosts();
      }

    } catch (err) {
      error = err.message;
      loading = false;
    }
  });

  async function loadSavedPosts() {
    try {
      savedPosts = await api.getSavedPosts();
    } catch (err) {
      error = err.message;
    }
  }

  async function loadUserImages() {
    try {
      console.log("Loading images for user ID:", userInfo.id);
      userImages = await api.getUserImages(userInfo.id);
      console.log("Received user images:", userImages);

      // Если массив пустой, добавим дополнительную проверку через прямой fetch
      if (userImages.length === 0) {
        console.log("No images found in API response, attempting direct fetch");
        try {
          const directResponse = await fetch(`/api/users/${userInfo.id}/images`);
          const directData = await directResponse.json();
          console.log("Direct fetch response:", directData);
        } catch (directError) {
          console.error("Direct fetch error:", directError);
        }
      }
    } catch (err) {
      console.error("Error loading user images:", err);
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

  async function deleteImage(imageId) {
    if (imageDeleteLoading) return;

    imageDeleteLoading = true;
    try {
      await api.deleteImage(imageId);
      // Удаляем изображение из списка
      userImages = userImages.filter(img => img.id !== imageId);
    } catch (err) {
      error = err.message;
    } finally {
      imageDeleteLoading = false;
    }
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

  // Функция для форматирования размера файла
  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' bytes';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
  }

	function isAdmin(userId) {
	  return userId === '1';
	}

function setTab(tab) {
  activeTab = tab;

  // Load admin data when needed
  if (tab === 'admin' && isAdmin(user.id) && allPosts.length === 0) {
    loadAllPosts();
  }
}

async function loadAllPosts() {
  if (!isAdmin(user.id)) return;

  loadingAllPosts = true;
  try {
    allPosts = await api.getPosts();
    loadingAllPosts = false;
  } catch (err) {
    error = err.message;
    loadingAllPosts = false;
  }
}

async function deletePost(postId) {
  if (!confirm('Вы уверены, что хотите удалить этот пост?')) {
    return;
  }

  try {
    await api.deletePost(postId);
    // Refresh the list
    allPosts = allPosts.filter(post => post.id !== postId);
  } catch (err) {
    error = err.message;
  }
}

  $: if (activeTab === 'saved' && user) {
    loadSavedPosts();
  }

  // Обработчик изменения активной вкладки
  $: if (activeTab === 'images' && user && userInfo) {
    console.log("Images tab activated, loading images");
    loadUserImages();
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
		  {#if isAdmin(userInfo.id)}
			<div class="admin-badge">Администратор</div>
		  {/if}
		  <p class="profile-email">{userInfo.email}</p>
            <p class="profile-date">Участник с {formatDate(userInfo.created_at)}</p>
            <div class="token-info">
              <p>Срок действия токена: <strong>{$tokenExpiration} сек.</strong></p>
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
			class="tab {activeTab === 'images' ? 'active' : ''}"
			on:click={() => setTab('images')}
		  >
			Изображения
		  </button>
		  <button
			class="tab {activeTab === 'settings' ? 'active' : ''}"
			on:click={() => setTab('settings')}
		  >
			Настройки
		  </button>

		  <!-- Show admin tab only for user with ID 1 -->
		  {#if isAdmin(user.id)}
			<button
			  class="tab admin-tab {activeTab === 'admin' ? 'active' : ''}"
			  on:click={() => setTab('admin')}
			>
			  Админ-панель
			</button>
			  <button
				class="tab admin-tab {activeTab === 'users' ? 'active' : ''}"
				on:click={() => setTab('users')}
			  >
				Пользователи
			  </button>
		  {/if}
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
        {:else if activeTab === 'images'}
          <div class="tab-panel">
            {#if loading}
              <div class="loading-images">
                <p>Загрузка изображений...</p>
              </div>
            {:else if userImages.length === 0}
              <div class="empty-images">
                <p>У вас пока нет загруженных изображений.</p>
                <p class="info-text">Изображения можно загрузить при создании или редактировании поста.</p>
                <button class="btn-refresh" on:click={() => loadUserImages()}>Обновить список</button>
              </div>
            {:else}
              <div class="images-grid">
                {#each userImages as image}
                  <div class="image-card">
                    <div class="image-preview clickable-image">
                      <img src={image.url_path} alt={image.original_filename} class="clickable-image" />
                    </div>
                    <div class="image-info">
                      <p class="image-filename" title={image.original_filename}>{image.original_filename}</p>
                      <p class="image-meta">
                        <span class="image-date">{formatDate(image.upload_date)}</span>
                        <span class="image-size">{formatFileSize(image.filesize)}</span>
                      </p>
                      <p class="image-post">
                        {#if image.post_id}
                          <Link to={`/post/${image.post_id}`}>Связанный пост</Link>
                        {:else}
                          <span class="no-post">Нет связанного поста</span>
                        {/if}
                      </p>
                    </div>
                    <div class="image-actions">
                      <a href={image.url_path} target="_blank" rel="noopener noreferrer" class="view-image-btn">
                        Просмотр
                      </a>
                      <button
                        class="delete-image-btn {imageDeleteLoading ? 'loading' : ''}"
                        on:click={() => deleteImage(image.id)}
                        disabled={imageDeleteLoading}
                      >
                        {imageDeleteLoading ? 'Удаление...' : 'Удалить'}
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
        {#if activeTab === 'admin'}
		  <div class="tab-panel">
			<h3>Панель администратора</h3>
			<p class="admin-info">Как администратор, вы можете управлять любыми постами, комментариями и изображениями.</p>

			{#if loadingAllPosts}
			  <div class="loading-container">
				<div class="loading-spinner"></div>
				<p>Загрузка всех постов...</p>
			  </div>
			{:else if allPosts.length === 0}
			  <div class="empty-state">
				<p>Постов пока нет.</p>
			  </div>
			{:else}
			  <h4>Все посты на платформе ({allPosts.length})</h4>
			  <div class="admin-post-list">
				{#each allPosts as post}
				  <div class="admin-post-item">
					<div class="admin-post-info">
					  <h5>
						<Link to={`/post/${post.id}`}>{post.title}</Link>
					  </h5>
					  <div class="admin-post-meta">
						<span class="admin-post-author">Автор: {post.username}</span>
						<span class="admin-post-date">Дата: {formatDate(post.created_at)}</span>
					  </div>
					</div>
					<div class="admin-post-actions">
					  <Link to={`/edit/${post.id}`} class="admin-edit-btn">Редактировать</Link>
					  <Link to={`/post/${post.id}`} class="admin-view-btn">Просмотр</Link>
					  <button class="admin-delete-btn" on:click={() => deletePost(post.id)}>Удалить</button>
					</div>
				  </div>
				{/each}
			  </div>
			{/if}
		  </div>
		{/if}
		{#if activeTab === 'users'}
		  <div class="tab-panel">
			<AdminUsers />
		  </div>
		{/if}
      </div>
    </div>
  {/if}
</div>

<style>
.admin-badge {
  display: inline-block;
  background-color: #dc3545;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  margin-bottom: 0.5rem;
}
.admin-tab {
  background-color: #dc3545;
  color: white;
}

.admin-tab:hover {
  background-color: #c82333;
}

.admin-info {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
}

.admin-post-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.admin-post-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #fff;
  border-radius: 5px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.admin-post-info {
  flex: 1;
}

.admin-post-info h5 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
}

.admin-post-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  font-size: 0.85rem;
  color: #6c757d;
}

.admin-post-actions {
  display: flex;
  gap: 0.5rem;
}

.admin-delete-btn {
  background-color: #dc3545;
  color: white;
  border: none;
  cursor: pointer;
}

.admin-delete-btn:hover {
  background-color: #c82333;
}
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

  .profile-container {
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .profile-header {
    padding: 2rem;
    background-color: #bbb;
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
    flex-wrap: wrap;
	background-color: #eee;
  }

  .tab {
    border: none;
    padding: 0.5rem 0.5rem;
    cursor: pointer;
    border-bottom: 4px solid transparent;
    transition: all 0.2s;
    font-family: inherit;
    font-size: inherit;
  }

  .tab:hover {
    color: #555;
    background-color: #f8f9fa;
  }

  .tab.active {
    color: #fff;
    border-bottom-color: #999;
    font-weight: bold;
  }

  .profile-content {
    padding: 2rem;
    background-color: #ddd;
  }

  .tab-panel {
    padding: 10px;
    margin-top: 10px;
    background-color: #f9f9f9;
  }

  .empty-posts, .empty-images, .loading-images {
    text-align: center;
    padding: 2rem;
    color: #6c757d;
  }

  .info-text {
    font-size: 0.9rem;
    color: #6c757d;
    margin-top: 0.5rem;
  }

  .btn-refresh {
    display: inline-block;
    margin-top: 1rem;
    padding: 0.5rem 1rem;
    background-color: #6c757d;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .btn-refresh:hover {
    background-color: #5a6268;
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

  .unsave-btn {
    background-color: #dc3545;
    color: white;
    border: none;
    padding: 0.25rem 0.5rem;
    font-size: 0.9rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .unsave-btn:hover {
    background-color: #c82333;
  }

  /* Стили для секции изображений */
  .images-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
    background-color: #eee;
  }

  .image-card {
    background-color: #fff;
    border-radius: 5px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .image-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 5px 10px rgba(0, 0, 0, 0.15);
  }

  .image-preview {
    height: 160px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #ddd;
    position: relative;
  }

  .image-preview img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }

  .image-info {
    padding: 1rem;
  }

  .image-filename {
    margin: 0 0 0.5rem;
    font-weight: bold;
    color: #343a40;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .image-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    color: #6c757d;
    margin: 0 0 0.5rem;
  }

  .image-post {
    font-size: 0.85rem;
    margin: 0;
  }

  .no-post {
    color: #6c757d;
    font-style: italic;
  }

  .image-actions {
    display: flex;
    border-top: 1px solid #dee2e6;
  }

  .view-image-btn, .delete-image-btn {
    flex: 1;
    padding: 0.5rem;
    text-align: center;
    border: none;
    font-size: 0.9rem;
    cursor: pointer;
    transition: background-color 0.2s;
    text-decoration: none;
  }

  .view-image-btn {
    background-color: #bbb;
    color: white;
  }

  .view-image-btn:hover {
    background-color: #138496;
  }

  .delete-image-btn {
    background-color: #dc3545;
    color: white;
  }

  .delete-image-btn:hover {
    background-color: #c82333;
  }

  .delete-image-btn.loading {
    background-color: #6c757d;
    cursor: not-allowed;
  }

  /* Адаптивность для мобильных устройств */
  @media (max-width: 576px) {
    .profile-tabs {
      flex-direction: column;
    }

    .tab {
      width: 100%;
      text-align: center;
      padding: 0.75rem;
      border-bottom: 1px solid #dee2e6;
    }

    .tab.active {
      border-bottom: 1px solid #dee2e6;
      border-left: 3px solid #007bff;
    }

    .post-item {
      flex-direction: column;
      align-items: flex-start;
    }

    .post-meta {
      margin: 0.5rem 0;
    }

    .post-actions {
      width: 100%;
      justify-content: space-between;
    }

    .images-grid {
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    }
  }
</style>