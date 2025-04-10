// src/utils/csrfUtils.js

/**
 * Get CSRF token from cookies
 * @param {string} type - Type of token to get ('access' or 'refresh')
 * @returns {string|null} - CSRF token or null if not found
 */
export function getCsrfTokenFromCookies(type = 'access') {
  const cookies = document.cookie.split(';')
    .map(cookie => cookie.trim())
    .reduce((acc, cookie) => {
      const [name, value] = cookie.split('=');
      acc[name] = value;
      return acc;
    }, {});

  // Explicitly return the correct token based on type
  if (type === 'refresh') {
    return cookies.csrf_refresh_token || null;
  }

  return cookies.csrf_access_token || null;
}

/**
 * Get all CSRF tokens from cookies
 * @returns {Object} - Object with access and refresh CSRF tokens
 */
export function getAllCsrfTokens() {
  const cookies = document.cookie.split(';')
    .map(cookie => cookie.trim())
    .reduce((acc, cookie) => {
      const [name, value] = cookie.split('=');
      acc[name] = value;
      return acc;
    }, {});

  return {
    access: cookies.csrf_access_token || null,
    refresh: cookies.csrf_refresh_token || null
  };
}