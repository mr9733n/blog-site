import { writable } from 'svelte/store';

// Проверка наличия токена в localStorage при инициализации
const storedToken = localStorage.getItem('authToken');
let initialUser = null;

// Время неактивности в миллисекундах, после которого не обновляем токен
// Измените в userStore.js
const INACTIVITY_THRESHOLD = 30000; // 30 секунд
let lastUserActivity = Date.now();

// Функция для проверки срока действия токена
export function isTokenExpired(token, bufferSeconds = 0) {
  if (!token) return true;

  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(window.atob(base64));

    // Проверка с буфером для заблаговременного обновления
    return payload.exp * 1000 <= Date.now() + (bufferSeconds * 1000);
  } catch (e) {
    console.error('Ошибка проверки токена', e);
    return true;
  }
}

// Обновление времени активности (добавьте где-то в основном файле приложения)
export function updateUserActivity() {
  lastUserActivity = Date.now();
}


if (storedToken) {
  // Используем новую функцию вместо дублирования кода
  if (!isTokenExpired(storedToken)) {
    try {
      const base64Url = storedToken.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(window.atob(base64));
      initialUser = { id: payload.sub };
    } catch (e) {
      console.error('Ошибка чтения токена', e);
      localStorage.removeItem('authToken');
    }
  } else {
    // Токен истек, удаляем его
    console.log('Token expired, removing');
    localStorage.removeItem('authToken');
  }
}
// Создаем хранилище с начальным значением
export const userStore = writable(initialUser);

// Функции API для работы с сервером
const API_URL = '/api';

export function checkTokenExpiration() {
  const storedToken = localStorage.getItem('authToken');
  if (!storedToken) return false;

  try {
    const base64Url = storedToken.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(window.atob(base64));

    // Check if token is expired (with 10s buffer)
    if (payload.exp * 1000 <= Date.now() + 10000) {
      console.log('Token expired or expiring soon');
      return false;
    }
    return true;
  } catch (e) {
    console.error('Error checking token expiration', e);
    return false;
  }
}

// Вспомогательная функция для запросов с авторизацией
async function authFetch(url, options = {}) {
  let token = localStorage.getItem('authToken');
  if (!token) {
    userStore.set(null); // Сбрасываем состояние, если нет токена
    throw new Error('Необходима авторизация');
  }

  // Проверяем срок действия токена ПЕРЕД запросом
  if (isTokenExpired(token)) {
    console.log('Токен истек, проверяем необходимость обновления');
    // Проверка времени неактивности для истекшего токена
    const currentTime = Date.now();
    const inactiveTime = currentTime - lastUserActivity;

    // Если пользователь был неактивен слишком долго, выходим
    if (inactiveTime > INACTIVITY_THRESHOLD) {
      console.log(`Пользователь был неактивен ${inactiveTime/1000} секунд, выход`);
      logout(); // Используем функцию logout вместо повторения кода
      throw new Error('Сессия истекла из-за неактивности. Пожалуйста, войдите снова.');
    }

    // Если пользователь активен, предварительно обновляем токен
    const refreshSuccess = await api.refreshToken();
    if (!refreshSuccess) {
      logout(); // Используем функцию logout
      throw new Error('Не удалось обновить сессию. Пожалуйста, войдите снова.');
    }

    // Получаем новый обновленный токен
    token = localStorage.getItem('authToken');
  }

  // Убедимся, что заголовки инициализированы
  if (!options.headers) {
    options.headers = {};
  }

  try {
    options.headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(url, options);
    console.log(`Response status for ${url}:`, response.status);

    // Если все еще получаем ошибку авторизации после обновления токена
    if (response.status === 401 || response.status === 422) {
      console.log('Ошибка авторизации после попытки обновления токена');
      logout(); // Используем функцию logout
      throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
    }

    return response;
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
}

// Добавьте эту функцию для централизованного выхода
function logout() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('tokenLifetime');
  userStore.set(null);
  window.location.href = '/login';
}

export const api = {
  // Вход пользователя
	async login(username, password) {
	  try {
		console.log('Attempting login for:', username);
		const response = await fetch(`${API_URL}/login`, {
		  method: 'POST',
		  headers: {
			'Content-Type': 'application/json'
		  },
		  body: JSON.stringify({ username, password })
		});

		if (!response.ok) {
		  const error = await response.json();
		  throw new Error(error.msg || 'Ошибка авторизации');
		}

		const data = await response.json();

		localStorage.setItem('authToken', data.access_token);
		localStorage.setItem('refreshToken', data.refresh_token);
		localStorage.setItem('tokenLifetime', data.token_lifetime.toString());

		// Декодируем токен для получения ID пользователя
		const base64Url = data.access_token.split('.')[1];
		const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
		const payload = JSON.parse(window.atob(base64));

		// Проверяем срок действия
		if (payload.exp * 1000 <= Date.now()) {
		  console.error('WARNING: Token is already expired!');
		}

		// Обновляем хранилище
		userStore.set({ id: payload.sub });

		return { success: true };
	  } catch (error) {
		console.error('Login error:', error);
		return { success: false, error: error.message };
	  }
	},
	async refreshToken() {
	  try {
		const refreshToken = localStorage.getItem('refreshToken');
		if (!refreshToken) {
		  throw new Error('No refresh token available');
		}

		const response = await fetch(`${API_URL}/refresh`, {
		  method: 'POST',
		  headers: {
			'Authorization': `Bearer ${refreshToken}`
		  }
		});

		if (!response.ok) {
		  throw new Error('Failed to refresh token');
		}

		const data = await response.json();
		localStorage.setItem('authToken', data.access_token);
		localStorage.setItem('tokenLifetime', data.token_lifetime.toString());

		return true;
	  } catch (error) {
		console.error('Error refreshing token:', error);
		// Clear tokens and user state
		localStorage.removeItem('authToken');
		localStorage.removeItem('refreshToken');
		localStorage.removeItem('tokenLifetime');
		userStore.set(null);
		return false;
	  }
	},
  // Регистрация пользователя
  async register(username, email, password) {
    try {
      const response = await fetch(`${API_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, email, password })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка регистрации');
      }
      
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  },
  
  // Получение списка постов с пагинацией
  async getPosts(limit = null, offset = null) {
    try {
      let url = `${API_URL}/posts`;
      const params = new URLSearchParams();
      
      if (limit !== null) params.append('limit', limit);
      if (offset !== null) params.append('offset', offset);
      
      const queryString = params.toString();
      if (queryString) url += `?${queryString}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Ошибка загрузки постов');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching posts:', error);
      return [];
    }
  },
  
  // Получение одного поста
  async getPost(id) {
    try {
      const response = await fetch(`${API_URL}/posts/${id}`);
      
      if (!response.ok) {
        throw new Error('Пост не найден');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching post:', error);
      throw error;
    }
  },
  
  // Создание поста
async createPost(title, content) {
  try {
    console.log('Creating post with data:', { title, content });

    const response = await authFetch(`${API_URL}/posts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ title, content })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.msg || 'Ошибка создания поста');
    }

    return await response.json();
  } catch (error) {
    console.error('Error creating post:', error);
    throw error;
  }
},
  
  // Обновление поста
  async updatePost(id, title, content) {
    try {
      const response = await authFetch(`${API_URL}/posts/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title, content })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка обновления поста');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error updating post:', error);
      throw error;
    }
  },
  
  // Удаление поста
  async deletePost(id) {
    try {
      const response = await authFetch(`${API_URL}/posts/${id}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка удаления поста');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error deleting post:', error);
      throw error;
    }
  },
  
  // Получение постов пользователя
  async getUserPosts(userId) {
    try {
      const response = await fetch(`${API_URL}/users/${userId}/posts`);
      
      if (!response.ok) {
        throw new Error('Ошибка загрузки постов пользователя');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching user posts:', error);
      return [];
    }
  },
  
  // Получение информации о текущем пользователе
  async getCurrentUser() {
    try {
      const response = await authFetch(`${API_URL}/me`);
      
      if (!response.ok) {
        throw new Error('Ошибка загрузки информации о пользователе');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching current user:', error);
      throw error;
    }
  },
  
  // Методы для работы с комментариями
  
  // Получение комментариев к посту
  async getPostComments(postId) {
    try {
      const response = await fetch(`${API_URL}/posts/${postId}/comments`);
      
      if (!response.ok) {
        throw new Error('Ошибка загрузки комментариев');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching comments:', error);
      return [];
    }
  },
  
  // Добавление комментария
  async addComment(postId, content) {
    try {
      const response = await authFetch(`${API_URL}/posts/${postId}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка добавления комментария');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error adding comment:', error);
      throw error;
    }
  },
  
  // Обновление комментария
  async updateComment(commentId, content) {
    try {
      const response = await authFetch(`${API_URL}/comments/${commentId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка обновления комментария');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error updating comment:', error);
      throw error;
    }
  },
  
  // Удаление комментария
  async deleteComment(commentId) {
    try {
      const response = await authFetch(`${API_URL}/comments/${commentId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка удаления комментария');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error deleting comment:', error);
      throw error;
    }
  },
	async updateTokenSettings(tokenLifetime, refreshTokenLifetime) {
	  try {
		const response = await authFetch(`${API_URL}/settings/token-settings`, {
		  method: 'PUT',
		  headers: {
			'Content-Type': 'application/json'
		  },
		  body: JSON.stringify({
			token_lifetime: tokenLifetime,
			refresh_token_lifetime: refreshTokenLifetime
		  })
		});

		if (!response.ok) {
		  const error = await response.json();
		  throw new Error(error.msg || 'Ошибка обновления настроек');
		}

		const result = await response.json();

		// Сохраняем новые токены
		if (result.access_token) {
		  localStorage.setItem('authToken', result.access_token);
		  localStorage.setItem('refreshToken', result.refresh_token);
		  console.log('Токены обновлены с новыми настройками срока жизни');
		}

		return result;
	  } catch (error) {
		console.error('Error updating token settings:', error);
		throw error;
	  }
	}
};