<!-- AdminUsers.svelte -->
<script>
  import { onMount } from 'svelte';
  import { Link, navigate } from "svelte-routing";
  import { api } from "../stores/apiService";
  import { checkAuth, isAdmin } from "../utils/authWrapper";
  import { userStore } from "../stores/userStore";
  import { formatDate, formatFileSize, maskEmail } from "../utils/formatUtils";
  import EditUser from './EditUser.svelte';

  let users = [];
  let loading = true;
  let error = null;
  let selectedUser = null;
  let userImages = [];
  let loadingImages = false;
  let blockingUser = false;
  let actionSuccess = null;
  let showUserImagesList = false;
  let editMode = false;
  let userToEdit = null;
  let showEmails = false;

  function toggleEmailVisibility(userId) {
    users = users.map(user => {
      if (user.id === userId) {
        return {
          ...user,
          showEmail: !user.showEmail
        };
      }
      return user;
    });
  }

  // Функция загрузки списка пользователей
  async function loadUsers() {
    loading = true;
    error = null;
    actionSuccess = null;

    try {
      users = await api.admin.getAllUsers();
      loading = false;
    } catch (err) {
      error = err.message;
      loading = false;
    }
  }

  // Функция для загрузки изображений пользователя
  async function loadUserImages(userId) {
    loadingImages = true;
    error = null;

    try {
      userImages = await api.users.getUserImages(userId);
      showUserImagesList = true;
      loadingImages = false;
    } catch (err) {
      error = err.message;
      loadingImages = false;
    }
  }

  // Функция блокировки/разблокировки пользователя
  async function toggleUserBlock(userId, currentBlockStatus) {
    if (blockingUser) return;

    blockingUser = true;
    error = null;
    actionSuccess = null;

    try {
      const newBlockStatus = !currentBlockStatus;
      await api.admin.toggleUserBlock(userId, newBlockStatus);

      // Обновляем список пользователей после действия
      await loadUsers();

      actionSuccess = newBlockStatus
        ? `Пользователь успешно заблокирован`
        : `Пользователь успешно разблокирован`;

      blockingUser = false;
    } catch (err) {
      error = err.message;
      blockingUser = false;
    }
  }

  // Функция удаления изображения
  async function deleteImage(imageId) {
    if (confirm('Вы действительно хотите удалить это изображение?')) {
      try {
        await api.images.deleteImage(imageId);
        // Обновляем список изображений
        userImages = userImages.filter(img => img.id !== imageId);
        actionSuccess = "Изображение успешно удалено";
      } catch (err) {
        error = err.message;
      }
    }
  }

  // Функция для редактирования пользователя
  function editUser(user) {
    userToEdit = user;
    editMode = true;
  }

  // Обработчик события обновления пользователя
  function handleUserUpdated(event) {
    // Обновляем данные пользователя в списке
    if (userToEdit) {
      const index = users.findIndex(u => u.id === userToEdit.id);
      if (index !== -1) {
        users[index] = {
          ...users[index],
          username: event.detail.username,
          email: event.detail.email
        };
      }
      actionSuccess = "Данные пользователя успешно обновлены";
      closeEditMode();
    }
  }

  // Закрыть режим редактирования
  function closeEditMode() {
    editMode = false;
    userToEdit = null;
  }

  // Загружаем список пользователей при монтировании компонента
  onMount(async () => {
    // Verify authentication AND admin status
    if (!(await checkAuth())) return;

    let user;
    userStore.subscribe(value => {
      user = value;
    });

    if (!isAdmin(user)) {
      navigate("/", { replace: true });
      return;
    }

    // Load admin data
    await loadUsers();
  });
</script>

<div class="admin-users">
  <h3>Управление пользователями</h3>

  {#if actionSuccess}
    <div class="success-message">
      {actionSuccess}
    </div>
  {/if}

  {#if error}
    <div class="error-message">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="loading-users">
      <p>Загрузка списка пользователей...</p>
    </div>
  {:else if editMode && userToEdit}
    <div class="edit-user-section">
      <div class="section-header">
        <button class="btn-back" on:click={closeEditMode}>
          &laquo; Назад к списку пользователей
        </button>
        <h4>Редактирование пользователя</h4>
      </div>
      <EditUser
        userId={userToEdit.id}
        username={userToEdit.username}
        email={userToEdit.email}
        adminMode={true}
        on:userUpdated={handleUserUpdated}
        on:cancel={closeEditMode}
      />
    </div>
  {:else}
    <!-- Подробный список пользователей -->
    {#if !showUserImagesList}
      <div class="users-table-container">
        <table class="users-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Email</th>
              <th>Created</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each users as user}
              <tr class="{user.is_blocked ? 'user-blocked' : ''}">
                <td>{user.id}</td>
                <td>{user.username}</td>
<td class="email-cell">
  {#if user.showEmail}
    <span>{user.email}</span>
  {:else}
    <span>{maskEmail(user.email)}</span>
  {/if}
  <button
    on:click={() => toggleEmailVisibility(user.id)}
    class="icon-button email-visibility-toggle"
    title={user.showEmail ? 'Hide email' : 'Show email'}
  >
    {#if user.showEmail}
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
        <circle cx="12" cy="12" r="3"/>
      </svg>
    {:else}
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
        <line x1="1" y1="1" x2="23" y2="23"/>
      </svg>
    {/if}
  </button>
</td>
                <td>{formatDate(user.created_at)}</td>
                <td>
                  {#if user.is_blocked}
                    <span class="status-blocked">Blocked</span>
                    {#if user.blocked_at}
                      <br>
                      <small>с {formatDate(user.blocked_at)}</small>
                    {/if}
                  {:else}
                    <span class="status-active">Active</span>
                  {/if}
<td class="user-actions">
  {#if user.id !== 1}
    <button
      class="icon-button {user.is_blocked ? 'btn-unblock' : 'btn-block'}"
      on:click={() => toggleUserBlock(user.id, user.is_blocked)}
      disabled={blockingUser}
      title={user.is_blocked ? 'Unblock User' : 'Block User'}
    >
      {#if user.is_blocked}
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
      {:else}
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 9.9-1"/>
        </svg>
      {/if}
    </button>
  {/if}
  <button
    class="icon-button btn-images"
    on:click={() => loadUserImages(user.id)}
    title="Open User Images"
  >
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
      <circle cx="8.5" cy="8.5" r="1.5"/>
      <polyline points="21 15 16 10 5 21"/>
    </svg>
  </button>
  <button
    class="icon-button btn-edit"
    on:click={() => editUser(user)}
    title="Edit User"
  >
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
  </button>
</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <!-- Список изображений выбранного пользователя -->
      <div class="user-images-section">
        <div class="section-header">
          <button class="btn-back" on:click={() => showUserImagesList = false}>
            &laquo; Назад к списку пользователей
          </button>
          <h4>Изображения пользователя</h4>
        </div>

        {#if loadingImages}
          <div class="loading-images">
            <p>Загрузка изображений...</p>
          </div>
        {:else if userImages.length === 0}
          <div class="empty-images">
            <p>У пользователя нет загруженных изображений.</p>
          </div>
        {:else}
          <div class="images-grid">
            {#each userImages as image}
              <div class="image-card">
                <div class="image-preview">
                  <img src={image.url_path} alt={image.original_filename} />
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
                    class="delete-image-btn"
                    on:click={() => deleteImage(image.id)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  .admin-users {
    margin-top: 20px;
  }

  .admin-users h3 {
    margin-bottom: 20px;
    color: #333;
  }

  .loading-users,
  .loading-images,
  .empty-images {
    padding: 20px;
    text-align: center;
    color: #666;
    background-color: #f5f5f5;
    border-radius: 5px;
    margin-bottom: 20px;
  }

  .success-message {
    padding: 15px;
    background-color: #d4edda;
    color: #155724;
    border-radius: 5px;
    margin-bottom: 20px;
  }

  .error-message {
    padding: 15px;
    background-color: #f8d7da;
    color: #721c24;
    border-radius: 5px;
    margin-bottom: 20px;
  }

  .section-header {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
  }

  .section-header h4 {
    margin: 0;
  }

  .btn-back {
    background-color: #6c757d;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 15px;
    margin-right: 15px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .btn-back:hover {
    background-color: #5a6268;
  }

  .users-table-container {
    overflow-x: auto;
  }

  .users-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
  }

  .users-table th,
  .users-table td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
  }

  .users-table th {
    background-color: #f8f9fa;
    font-weight: bold;
  }

  .users-table tr:hover {
    background-color: #f5f5f5;
  }

  .user-blocked {
    background-color: #fff8f8;
  }

  .status-active {
    color: #28a745;
    font-weight: bold;
  }

  .status-blocked {
    color: #dc3545;
    font-weight: bold;
  }

  .user-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }

  .btn-block,
  .btn-unblock,
  .btn-images,
  .btn-edit {
    padding: 6px 12px;
    font-size: 0.85rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .btn-block {
    background-color: #dc3545;
    color: white;
  }

  .btn-block:hover {
    background-color: #c82333;
  }

  .btn-unblock {
    background-color: #28a745;
    color: white;
  }

  .btn-unblock:hover {
    background-color: #218838;
  }

  .btn-images {
    background-color: #17a2b8;
    color: white;
  }

  .btn-images:hover {
    background-color: #138496;
  }

  .btn-edit {
    background-color: #6c757d;
    color: white;
  }

  .btn-edit:hover {
    background-color: #5a6268;
  }

  /* Стили для списка изображений */
  .user-images-section,
  .edit-user-section {
    margin-top: 15px;
  }

  .images-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
    margin-top: 20px;
  }

  .image-card {
    background-color: white;
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
    background-color: #f8f9fa;
    position: relative;
  }

  .image-preview img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }

  .image-info {
    padding: 15px;
  }

  .image-filename {
    margin: 0 0 10px;
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
    margin: 0 0 10px;
  }

  .image-post {
    font-size: 0.85rem;
    margin: 0;
  }

  .image-post a {
    color: #007bff;
    text-decoration: none;
  }

  .image-post a:hover {
    text-decoration: underline;
  }

  .no-post {
    color: #6c757d;
    font-style: italic;
  }

  .image-actions {
    display: flex;
    border-top: 1px solid #dee2e6;
  }

  .view-image-btn,
  .delete-image-btn {
    flex: 1;
    padding: 10px;
    text-align: center;
    border: none;
    font-size: 0.9rem;
    cursor: pointer;
    transition: background-color 0.2s;
    text-decoration: none;
  }

  .view-image-btn {
    background-color: #17a2b8;
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

  .icon-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 5px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #666;
    transition: color 0.2s;
  }

  .icon-button:hover {
    color: #000;
  }

  .icon-button svg {
    width: 20px;
    height: 20px;
  }

  .icon-button:disabled {
    color: #ccc;
    cursor: not-allowed;
  }

  .email-cell {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .email-visibility-toggle {
    margin-left: 10px;
  }
  /* Адаптивность для мобильных устройств */
  @media (max-width: 768px) {
    .users-table th,
    .users-table td {
      padding: 8px 10px;
      font-size: 0.9rem;
    }

    .user-actions {
      flex-direction: column;
    }

    .user-actions button {
      margin: 3px 0;
    }

    .images-grid {
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 15px;
    }
  }

</style>