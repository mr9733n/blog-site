// src/stores/apiService.js
import { postsAPI } from './api/postsAPI';
import { usersAPI } from './api/usersAPI';
import { commentsAPI } from './api/commentsAPI';
import { imagesAPI } from './api/imagesAPI';
import { adminAPI } from './api/adminAPI';
import { settingsAPI } from './api/settingsAPI';
import { debugApiCall } from './api/apiUtils';

// Объединяем все API в один экспорт
export const api = {
  posts: postsAPI,
  users: usersAPI,
  comments: commentsAPI,
  images: imagesAPI,
  admin: adminAPI,
  settings: settingsAPI
};

// Экспортируем утилиты при необходимости
export { debugApiCall };