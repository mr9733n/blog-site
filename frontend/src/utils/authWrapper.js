// src/utils/AuthWrapper.js
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
    // This will automatically trigger token refresh if needed
    await authFetch('/api/me');
    return true;
  } catch (err) {
    console.warn('Authentication check failed:', err.message);
    navigate(redirectTo, { replace: true });
    return false;
  }
}

/**
 * Helper function to determine if a user is an admin
 * @param {Object} user - User object from userStore
 * @returns {boolean} - True if user is admin
 */
export function isAdmin(user) {
  return user && user.id === '1'; // Admin has ID 1
}

/**
 * Check if the current user can edit the specified content
 * @param {Object} user - User object from userStore
 * @param {number|string} authorId - Author ID of the content
 * @returns {boolean} - True if user can edit
 */
export function canEdit(user, authorId) {
  if (!user) return false;

  // Admin can edit anything
  if (isAdmin(user)) return true;

  // Users can edit their own content
  return user.id === authorId.toString();
}