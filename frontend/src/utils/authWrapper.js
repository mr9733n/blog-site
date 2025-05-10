// src/utils/authWrapper.js
import { navigate } from 'svelte-routing';
import { authFetch } from '../stores/authService';

/**
 * A utility function for checking authentication on protected pages
 * and triggering token refresh if needed
 *
 * @param {string} redirectTo - Path to redirect if authentication fails
 * @returns {Promise<boolean>} - True if authenticated, otherwise redirects
 */
export async function checkAuth(redirectTo = '/login') {
  try {
    // Пытаемся получить текущие данные пользователя, что вызовет обновление токена при необходимости
    const response = await fetch('/api/me', {
      credentials: 'include',
      cache: 'no-store'
    });

    return response.ok;
  } catch (err) {
    console.warn('Auth check failed:', err);
    return false;
  }
}

/**
 * Helper function to determine if a user is an admin
 * @param {Object} user - User object from userStore
 * @returns {boolean} - True if user is admin
 */
export function isAdmin(user) {
  console.log('Checking admin status for user:', user);

  // Handle both string and number IDs
  if (!user || user.id === undefined) return false;

  try {
    // Убедимся, что user.id всегда обрабатывается как строка для сравнения
    const userId = String(user.id);
    return userId === '1'; // Администратор имеет ID=1
  } catch (error) {
    console.error('Error in isAdmin check:', error);
    return false;
  }
}

/**
 * Check if the current user can edit the specified content
 * @param {Object} user - User object from userStore
 * @param {number|string} authorId - Author ID of the content
 * @returns {boolean} - True if user can edit
 */
export function canEdit(user, authorId) {
  if (!user) return false;

  try {
    // Сначала проверяем на права администратора
    if (isAdmin(user)) return true;

    // Затем проверяем, является ли пользователь автором
    const userId = String(user.id);
    const contentAuthorId = String(authorId);

    return userId === contentAuthorId;
  } catch (error) {
    console.error('Error in canEdit check:', error);
    return false;
  }
}