// Обновите функции в src/utils/csrfUtils.js

/**
 * Get CSRF token from cookies with more robust error handling
 * @param {string} type - 'access' or 'refresh'
 * @returns {string|null} - CSRF token or null if not found
 */
export function getCsrfTokenFromCookies(type = 'access') {
  try {
    const cookieName = type === 'refresh' ? 'csrf_refresh_token' : 'csrf_access_token';

    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === cookieName) {
        return value;
      }
    }

    // Логируем отсутствие CSRF токена в куках для отладки
    console.log(`CSRF token not found in cookies: ${cookieName}`);
    console.log('Available cookies:', document.cookie);
    return null;
  } catch (error) {
    console.error('Error getting CSRF token from cookies:', error);
    return null;
  }
}

/**
 * Get CSRF state from cookies with enhanced debugging
 * @returns {string|null} - CSRF state or null if not found
 */
export function getCsrfStateFromCookies() {
  try {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrf_state') {
        return value;
      }
    }

    // Логируем отсутствие CSRF state в куках для отладки
    console.log('CSRF state not found in cookies');
    return null;
  } catch (error) {
    console.error('Error getting CSRF state from cookies:', error);
    return null;
  }
}

/**
 * Alternative method to get CSRF token from response headers
 * @param {Response} response - Fetch API response object
 * @param {string} type - 'access' or 'refresh'
 * @returns {string|null} - CSRF token or null if not found
 */
export function getCsrfTokenFromHeaders(response, type = 'access') {
  if (!response || !response.headers) return null;

  // Получаем CSRF токен из заголовка ответа
  const csrfToken = response.headers.get('X-CSRF-TOKEN');

  if (csrfToken) {
    console.log(`CSRF token found in response headers: ${csrfToken.substring(0, 8)}...`);
    return csrfToken;
  }

  return null;
}

/**
 * Check for X-CSRF-STATE header in response
 * @param {Response} response - Fetch API response
 * @returns {string|null} - CSRF state from header or null
 */
export function getCsrfStateFromHeaders(response) {
  if (!response || !response.headers) return null;

  return response.headers.get('X-CSRF-STATE');
}

/**
 * Get complete CSRF data with enhanced debugging
 * @returns {Object} - Object with access token, refresh token, and state
 */
export function getAllCsrfData() {
  const access = getCsrfTokenFromCookies('access');
  const refresh = getCsrfTokenFromCookies('refresh');
  const state = getCsrfStateFromCookies();

  // Логируем CSRF данные для отладки
  console.log('CSRF Data:', {
    access: access ? `${access.substring(0, 8)}...` : null,
    refresh: refresh ? `${refresh.substring(0, 8)}...` : null,
    state: state ? `${state.substring(0, 8)}...` : null
  });

  return { access, refresh, state };
}