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
  console.log('Checking admin status for user:', user);

  // Handle both string and number IDs
  if (!user || user.id === undefined) return false;

  // Convert both to strings for comparison (handles both number and string IDs)
  const userId = String(user.id);
  const adminId = '1';

  console.log(`Comparing user ID (${userId}) with admin ID (${adminId})`);
  return userId === adminId;
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
  return String(user.id) === String(authorId);
}