import { writable, derived } from 'svelte/store';

// Проверка наличия токена в localStorage при инициализации
const storedToken = localStorage.getItem('authToken');
let initialUser = null;

// Время неактивности в миллисекундах, после которого не обновляем токен
// Измените в userStore.js
export const INACTIVITY_THRESHOLD = 5 * 60 * 1000; // 300 seconds
let lastUserActivity = Date.now();

export const tokenRefreshLoading = writable(false);

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

export function isAdmin(user) {
  return user && user.id === '1'; // Admin is user with ID 1
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

export const tokenExpiration = derived(
  userStore,
  ($userStore, set) => {
    const checkExpiration = () => {
      const token = localStorage.getItem('authToken');
      if (!token) return set(0);

      try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(window.atob(base64));
        set(Math.max(0, Math.floor(payload.exp - Date.now()/1000)));
      } catch (e) {
        console.error('Ошибка проверки токена', e);
        set(0);
      }
    };

    // Initial check
    checkExpiration();

    // Setup interval
    const interval = setInterval(checkExpiration, 1000);

    // Cleanup on unsubscribe
    return () => clearInterval(interval);
  }
);

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
    userStore.set(null);
    throw new Error('Необходима авторизация');
  }

  // Если токен истек — пробуем рефрешнуть
  if (isTokenExpired(token)) {
    console.log('Access-токен истёк. Пытаемся обновить через refresh...');
    const now = Date.now();
    const inactiveTime = now - lastUserActivity;

    if (inactiveTime > INACTIVITY_THRESHOLD) {
      console.warn(`⏳ Неактивность ${inactiveTime / 1000} сек — выходим.`);
      logout();
      throw new Error('Сессия завершена из-за неактивности.');
    }

    console.log('🔁 Попытка обновления токена через refresh...');
    const refreshSuccess = await api.refreshToken();
    if (!refreshSuccess) {
      console.warn('Рефреш не удался. Выполняем выход.');
      logout();
      throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
    }

    // После успешного рефреша получаем новый access token
    token = localStorage.getItem('authToken');
  }

  if (!options.headers) {
    options.headers = {};
  }

  try {
    options.headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(url, options);

    if (response.status === 401 || response.status === 422) {
      console.warn('Ошибка авторизации после попытки рефреша. Logout.');
      logout();
      throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
    }

    return response;
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
}

// Добавьте эту функцию для централизованного выхода
export function logout() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('tokenLifetime');
  localStorage.removeItem('refreshTokenLifetime');
  userStore.set(null);
  window.location.href = '/';
}

export const api = {
    // Вход пользователя
	async login(username, password) {
	  try {
		console.log('Attempting login for:', username);

		// Проверка формата ввода на стороне клиента (первичный уровень защиты)
		if (username.includes("'") || username.includes('"') || username.includes(';') ||
			password.includes("'") || password.includes('"') || password.includes(';')) {
		  console.warn('Suspicious characters detected in login credentials');
		  // Можем либо отказать сразу, либо продолжить и дать серверу обработать это
		  // return { success: false, error: 'Логин или пароль содержат недопустимые символы' };
		}

		const response = await fetch(`${API_URL}/login`, {
		  method: 'POST',
		  headers: {
			'Content-Type': 'application/json'
		  },
		  body: JSON.stringify({ username, password })
		});

		if (response.status === 401) {
		  // Для ошибок авторизации - более дружелюбное сообщение
		  return { success: false, error: 'Неверный логин или пароль' };
		} else if (!response.ok) {
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
		tokenRefreshLoading.set(true);
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
	  } finally {
		tokenRefreshLoading.set(false);
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

		// For admin users, we might want to get all posts
		// You could also create a new endpoint like /api/admin/posts
		// For now, we'll use the existing endpoint
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
		},
		async savePost(postId) {
	  try {
		const response = await authFetch(`${API_URL}/posts/${postId}/save`, {
		  method: 'POST'
		});

		if (!response.ok) {
		  const error = await response.json();
		  throw new Error(error.msg || 'Ошибка сохранения поста');
		}

		return await response.json();
	  } catch (error) {
		console.error('Error saving post:', error);
		throw error;
	  }
	},

	async unsavePost(postId) {
	  try {
		const response = await authFetch(`${API_URL}/posts/${postId}/unsave`, {
		  method: 'POST'
		});

		if (!response.ok) {
		  const error = await response.json();
		  throw new Error(error.msg || 'Ошибка удаления поста из сохранённых');
		}

		return await response.json();
	  } catch (error) {
		console.error('Error unsaving post:', error);
		throw error;
	  }
	},

	async getSavedPosts() {
	  try {
		const response = await authFetch(`${API_URL}/saved/posts`);

		if (!response.ok) {
		  throw new Error('Ошибка загрузки сохранённых постов');
		}

		return await response.json();
	  } catch (error) {
		console.error('Error fetching saved posts:', error);
		return [];
	  }
	},

	async isPostSaved(postId) {
	  try {
		const response = await authFetch(`${API_URL}/posts/${postId}/is_saved`);

		if (!response.ok) {
		  throw new Error('Ошибка проверки сохранения поста');
		}

		const data = await response.json();
		return data.is_saved;
	  } catch (error) {
		console.error('Error checking if post is saved:', error);
		return false;
	  }
	},


  async uploadImage(file, postId = null) {
	  try {
		const formData = new FormData();
		formData.append('file', file);

		if (postId) {
		  formData.append('post_id', postId);
		}

		const response = await authFetch(`${API_URL}/images/upload`, {
		  method: 'POST',
		  body: formData
		});

		if (!response.ok) {
		  // Проверяем тип контента ответа
		  const contentType = response.headers.get('content-type');

		  if (contentType && contentType.includes('application/json')) {
			// Если JSON, парсим обычным способом
			const error = await response.json();
			throw new Error(error.msg || 'Ошибка загрузки изображения');
		  } else {
			// Если не JSON (например HTML), показываем более понятное сообщение
			if (response.status === 413) {
			  throw new Error('Файл слишком большой. Максимальный размер - 5 МБ');
			} else {
			  // Для других ошибок показываем код статуса
			  throw new Error(`Ошибка сервера (${response.status}). Попробуйте файл меньшего размера или другого формата.`);
			}
		  }
		}

		return await response.json();
	  } catch (error) {
		console.error('Error uploading image:', error);
		throw error;
	  }
	},

  async getPostImages(postId) {
    try {
      const response = await fetch(`${API_URL}/posts/${postId}/images`);

      if (!response.ok) {
        throw new Error('Ошибка получения изображений');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching post images:', error);
      return [];
    }
  },

  async getUserImages(userId, limit = null) {
    try {
      let url = `${API_URL}/users/${userId}/images`;

      if (limit) {
        url += `?limit=${limit}`;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('Ошибка получения изображений пользователя');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching user images:', error);
      return [];
    }
  },

  async deleteImage(imageId) {
    try {
      const response = await authFetch(`${API_URL}/images/${imageId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка удаления изображения');
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting image:', error);
      throw error;
    }
  },

  async attachImageToPost(imageId, postId) {
    try {
      const response = await authFetch(`${API_URL}/images/${imageId}/post/${postId}`, {
        method: 'PUT'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка привязки изображения к посту');
      }

      return await response.json();
    } catch (error) {
      console.error('Error attaching image to post:', error);
      throw error;
    }
  },

  async detachImageFromPost(imageId) {
    try {
      const response = await authFetch(`${API_URL}/images/${imageId}/post`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Ошибка отвязки изображения от поста');
      }

      return await response.json();
    } catch (error) {
      console.error('Error detaching image from post:', error);
      throw error;
    }
  },
  // Получение списка всех пользователей (только для админа)
async getAllUsers() {
  try {
    const response = await authFetch(`${API_URL}/admin/users`);

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Недостаточно прав для выполнения операции');
      }
      throw new Error('Ошибка получения списка пользователей');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching all users:', error);
    throw error;
  }
},

// Получение подробной информации о пользователе (только для админа)
async getUserDetails(userId) {
  try {
    const response = await authFetch(`${API_URL}/admin/users/${userId}`);

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Недостаточно прав для выполнения операции');
      } else if (response.status === 404) {
        throw new Error('Пользователь не найден');
      }
      throw new Error('Ошибка получения данных пользователя');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching user details:', error);
    throw error;
  }
},

// Блокировка/разблокировка пользователя (только для админа)
async toggleUserBlock(userId, blockStatus) {
  try {
    const response = await authFetch(`${API_URL}/admin/users/${userId}/block`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ blocked: blockStatus })
    });

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Недостаточно прав для выполнения операции');
      }
      const error = await response.json();
      throw new Error(error.msg || 'Ошибка изменения блокировки пользователя');
    }

    return await response.json();
  } catch (error) {
    console.error('Error toggling user block status:', error);
    throw error;
  }
},

// Обновление данных пользователя (только для админа)
async updateUserData(userId, userData) {
  try {
    const response = await authFetch(`${API_URL}/admin/users/${userId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Недостаточно прав для выполнения операции');
      }
      const error = await response.json();
      throw new Error(error.msg || 'Ошибка обновления данных пользователя');
    }

    return await response.json();
  } catch (error) {
    console.error('Error updating user data:', error);
    throw error;
  }
}
};