// src/stores/authService.js
import { userStore, tokenRefreshLoading, getLastUserActivity, INACTIVITY_THRESHOLD } from './userStore';
import { API_URL } from '../config';

// Last token refresh timestamp to prevent too frequent refresh attempts
let lastRefreshAttempt = 0;
const MIN_REFRESH_INTERVAL = 5000; // 5 seconds minimum between refresh attempts

/**
 * Helper function for authenticated requests with auto token refresh
 * @param {string} url - API URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} - Fetch response
 */
export async function authFetch(url, options = {}) {
  let token = localStorage.getItem('authToken');

  if (!token) {
    userStore.set(null);
    throw new Error('Authentication required');
  }

  // Check if token is expired
  if (isTokenExpired(token)) {
    console.log('⏳ Access token expired. Attempting refresh...');

    // Check for user inactivity
    const now = Date.now();
    const lastUserActivity = getLastUserActivity();
    const inactiveTime = now - lastUserActivity;

    if (inactiveTime > INACTIVITY_THRESHOLD) {
      console.warn(`⏳ Inactive for ${inactiveTime / 1000} seconds — logging out.`);
      logout();
      throw new Error('Session ended due to inactivity.');
    }

    // Attempt to refresh token
    const refreshSuccess = await refreshToken();
    if (!refreshSuccess) {
      console.warn('⚠️ Refresh failed. Logging out.');
      logout();
      throw new Error('Session expired. Please log in again.');
    }

    // Get new token after successful refresh
    token = localStorage.getItem('authToken');
  }

  // Set up auth headers
  if (!options.headers) {
    options.headers = {};
  }

  try {
    options.headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(url, options);

    // Handle auth errors
    if (response.status === 401 || response.status === 422) {
      console.warn('⚠️ Authorization error after refresh attempt. Logging out.');
      logout();
      throw new Error('Session expired. Please log in again.');
    }

    return response;
  } catch (error) {
    console.error('❌ Fetch error:', error);
    throw error;
  }
}

/**
 * Check if token is expired
 * @param {string} token - JWT token
 * @param {number} bufferSeconds - Buffer time before expiration (to refresh early)
 * @returns {boolean} - True if token is expired or will expire soon
 */
export function isTokenExpired(token, bufferSeconds = 60) {
  if (!token) return true;

  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(window.atob(base64));

    // Check with buffer for preemptive renewal
    return payload.exp * 1000 <= Date.now() + (bufferSeconds * 1000);
  } catch (e) {
    console.error('❌ Error checking token expiration', e);
    return true;
  }
}

/**
 * Simple token expiration check without refresh
 * @returns {boolean} - True if token is valid, false if expired
 */
export function checkTokenExpiration() {
  const storedToken = localStorage.getItem('authToken');
  if (!storedToken) return false;

  try {
    // No buffer - only check if truly expired
    return !isTokenExpired(storedToken, 0);
  } catch (e) {
    console.error('❌ Error checking token expiration', e);
    return false;
  }
}

/**
 * Refresh the authentication token
 * @returns {Promise<boolean>} - True if refresh was successful
 */
export async function refreshToken() {
  // Prevent multiple simultaneous refresh attempts
  const now = Date.now();
  if (now - lastRefreshAttempt < MIN_REFRESH_INTERVAL) {
    console.log('🔄 Token refresh throttled. Last attempt:', new Date(lastRefreshAttempt).toISOString());
    // Wait for the current refresh to complete
    return new Promise(resolve => {
      const checkInterval = setInterval(() => {
        if (!tokenRefreshLoading) {
          clearInterval(checkInterval);
          resolve(checkTokenExpiration());
        }
      }, 100);
    });
  }

  lastRefreshAttempt = now;
  console.log('🔄 Attempting token refresh at:', new Date(now).toISOString());

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
    console.log('✅ Token refreshed successfully');

    return true;
  } catch (error) {
    console.error('❌ Error refreshing token:', error);

    // Clear tokens and user state on failure
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('tokenLifetime');
    userStore.set(null);

    return false;
  } finally {
    tokenRefreshLoading.set(false);
  }
}

/**
 * Logout the current user
 */
export function logout() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('tokenLifetime');
  localStorage.removeItem('refreshTokenLifetime');
  userStore.set(null);

  if (typeof window !== 'undefined') {
    window.location.href = '/';
  }
}

/**
 * Login with username and password
 * @param {string} username
 * @param {string} password
 * @returns {Promise<Object>} - Login result
 */
export async function login(username, password) {
  try {
    console.log('🔑 Attempting login for:', username);

    // Basic input validation
    if (username.includes("'") || username.includes('"') || username.includes(';') ||
        password.includes("'") || password.includes('"') || password.includes(';')) {
      console.warn('⚠️ Suspicious characters detected in login credentials');
    }

    const response = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password })
    });

    if (response.status === 401) {
      return { success: false, error: 'Invalid username or password' };
    } else if (!response.ok) {
      const error = await response.json();
      throw new Error(error.msg || 'Authentication error');
    }

    const data = await response.json();

    // Store tokens
    localStorage.setItem('authToken', data.access_token);
    localStorage.setItem('refreshToken', data.refresh_token);
    localStorage.setItem('tokenLifetime', data.token_lifetime.toString());

    // Parse user info from token
    const base64Url = data.access_token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(window.atob(base64));

    // Warn if token is already expired
    if (payload.exp * 1000 <= Date.now()) {
      console.error('⚠️ WARNING: Token is already expired!');
    }

    // Update user store
    userStore.set({ id: payload.sub });
    console.log('✅ Login successful');

    return { success: true };
  } catch (error) {
    console.error('❌ Login error:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Register a new user
 * @param {string} username
 * @param {string} email
 * @param {string} password
 * @returns {Promise<Object>} - Registration result
 */
export async function register(username, email, password) {
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
      throw new Error(error.msg || 'Registration error');
    }

    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}