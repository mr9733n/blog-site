// src/utils/csrfUtils.js
// Extend with CSRF State functionality

/**
 * Get CSRF token from cookies
 * @param {string} type - 'access' or 'refresh'
 * @returns {string|null} - CSRF token or null if not found
 */
export function getCsrfTokenFromCookies(type = 'access') {
  const cookieName = type === 'refresh' ? 'csrf_refresh_token' : 'csrf_access_token';

  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === cookieName) {
      return value;
    }
  }
  return null;
}

/**
 * Get CSRF state from cookies
 * @returns {string|null} - CSRF state or null if not found
 */
export function getCsrfStateFromCookies() {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrf_state') {
      return value;
    }
  }
  return null;
}

/**
 * Get all CSRF tokens from cookies
 * @returns {Object} - Object with access and refresh CSRF tokens
 */
export function getAllCsrfTokens() {
  return {
    access: getCsrfTokenFromCookies('access'),
    refresh: getCsrfTokenFromCookies('refresh')
  };
}

/**
 * Get complete CSRF data (tokens and state)
 * @returns {Object} - Object with access token, refresh token, and state
 */
export function getAllCsrfData() {
  return {
    access: getCsrfTokenFromCookies('access'),
    refresh: getCsrfTokenFromCookies('refresh'),
    state: getCsrfStateFromCookies()
  };
}