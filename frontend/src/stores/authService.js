// src/stores/authService.js
import { userStore, tokenRefreshLoading, getLastUserActivity, INACTIVITY_THRESHOLD } from './userStore';
import { API_URL } from '../config';
import { getCsrfTokenFromCookies, getAllCsrfTokens } from '../utils/csrfUtils';

// Last token refresh timestamp to prevent too frequent refresh attempts
let lastRefreshAttempt = 0;
let csrfTokens = { access: null, refresh: null };
const MIN_REFRESH_INTERVAL = 5000; // 5 seconds minimum between refresh attempts

// Update CSRF tokens (called at login and refresh)
export function updateCsrfTokens() {
  csrfTokens = getAllCsrfTokens();
  return csrfTokens;
}

// Get current CSRF token based on type
export function getCsrfToken(type = 'access') {
  if (!csrfTokens.access && !csrfTokens.refresh) {
    updateCsrfTokens();
  }

  return type === 'refresh' ? csrfTokens.refresh : csrfTokens.access;
}

// Save token lifetimes to localStorage
export function saveTokenLifetimes(tokenLifetime, refreshTokenLifetime) {
  if (tokenLifetime) {
    localStorage.setItem('tokenLifetime', tokenLifetime.toString());
  }
  if (refreshTokenLifetime) {
    localStorage.setItem('refreshTokenLifetime', refreshTokenLifetime.toString());
  }
}

// Clear token lifetimes from localStorage
export function clearTokenLifetimes() {
  localStorage.removeItem('tokenLifetime');
  localStorage.removeItem('refreshTokenLifetime');
}

/**
 * Helper function for authenticated requests
 * With cookie-based auth, we don't need to manually add tokens
 *
 * @param {string} url - API URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} - Fetch response
 */
export async function authFetch(url, options = {}) {
  // Update CSRF tokens if not set
  if (!csrfTokens.access && !csrfTokens.refresh) {
    updateCsrfTokens();
  }

  // Include credentials to ensure cookies are sent
  const fetchOptions = {
    ...options,
    credentials: 'include'
  };

  // Configure headers
  fetchOptions.headers = {
    ...fetchOptions.headers || {}
  };

  // Add the appropriate CSRF token based on the endpoint
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method)) {
    // Use refresh token for refresh endpoint
    if (url.endsWith('/refresh')) {
      if (csrfTokens.refresh) {
        fetchOptions.headers['X-CSRF-TOKEN'] = csrfTokens.refresh;
      }
    } else if (csrfTokens.access) {
      // Use access token for all other endpoints
      fetchOptions.headers['X-CSRF-TOKEN'] = csrfTokens.access;
    }
  }

  try {
    // Try the fetch with current auth cookie
    const response = await fetch(url, fetchOptions);

    // Update CSRF tokens if provided in response headers
    const newCsrfToken = response.headers.get('X-CSRF-TOKEN');
    if (newCsrfToken) {
      // We can't know which token was updated, so update both from cookies
      updateCsrfTokens();
    }

    // Handle auth errors - if we get a 401 or 403, try to refresh token once
    if (response.status === 401 || response.status === 403) {
      console.log('⏳ Token expired. Attempting refresh...');

      // Only check inactivity if the refresh fails
      // Try to refresh the token first
      const refreshSuccess = await refreshToken();

      if (!refreshSuccess) {
        // Only check inactivity if refresh failed
        const now = Date.now();
        const lastUserActivity = getLastUserActivity();
        const inactiveTime = now - lastUserActivity;

        if (inactiveTime > INACTIVITY_THRESHOLD) {
          console.warn(`⏳ Inactive for ${inactiveTime / 1000} seconds — logging out.`);
          await logout(true);
          throw new Error('Session ended due to inactivity.');
        }

        console.warn('⚠️ Refresh failed. Logging out.');
        await logout(true);
        throw new Error('Session expired. Please log in again.');
      }

      // Retry the original request with the new token (cookie)
      return fetch(url, fetchOptions);
    }

    return response;
  } catch (error) {
    console.error('❌ Fetch error:', error);
    throw error;
  }
}

/**
 * Check if user is authenticated
 * @returns {Promise<boolean>} - True if authenticated
 */
export async function isAuthenticated() {
  try {
    const response = await fetch(`${API_URL}/me`, {
      credentials: 'include' // Include cookies
    });

    return response.ok;
  } catch (error) {
    console.error('Auth check error:', error);
    return false;
  }
}

/**
 * Simple token validation check
 * @returns {Promise<boolean>} - True if token is valid
 */
export async function checkTokenExpiration() {
  return await isAuthenticated();
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
    return new Promise(resolve => {
      const checkInterval = setInterval(async () => {
        if (!tokenRefreshLoading.get()) {
          clearInterval(checkInterval);
          // Check if we're authenticated after the other refresh completed
          resolve(await isAuthenticated());
        }
      }, 100);
    });
  }

  lastRefreshAttempt = now;
  console.log('🔄 Attempting token refresh at:', new Date(now).toISOString());

  // Get the latest refresh CSRF token
  updateCsrfTokens();
  const refreshCsrfToken = getCsrfToken('refresh');

  if (!refreshCsrfToken) {
    console.error('❌ No refresh CSRF token available');
    return false;
  }

  try {
    tokenRefreshLoading.set(true);

    const response = await fetch(`${API_URL}/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRF-TOKEN': refreshCsrfToken
      }
    });

    if (!response.ok) {
      console.error('Token refresh failed with status:', response.status);
      throw new Error('Failed to refresh token');
    }

    // Update CSRF tokens after refresh
    updateCsrfTokens();

    // Get user info from the response if available
    try {
      const data = await response.json();

      // Save token lifetimes from response
      if (data && data.token_lifetime) {
        const tokenLifetime = data.token_lifetime;
        const refreshTokenLifetime = data.refresh_token_lifetime;
        saveTokenLifetimes(tokenLifetime, refreshTokenLifetime);
      }

      if (data && data.user) {
        userStore.set({ id: data.user.id });
      }
    } catch (jsonError) {
      console.warn('Could not parse JSON from refresh token response:', jsonError);
      // Continue anyway as the cookies may have been set
    }

    console.log('✅ Token refreshed successfully');
    return true;
  } catch (error) {
    console.error('❌ Error refreshing token:', error);
    return false;
  } finally {
    tokenRefreshLoading.set(false);
  }
}

/**
 * Logout the current user
 * @param {boolean} [forceClear=false] - Force clear local storage even if the server logout fails
 */
export async function logout(forceClear = false) {
  let logoutSuccess = false;

  try {
    // Get the latest access CSRF token
    const accessCsrfToken = getCsrfToken('access');

    // Call logout endpoint to clear server-side cookies
    const response = await fetch(`${API_URL}/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRF-TOKEN': accessCsrfToken
      }
    });

    logoutSuccess = response.ok;

    // Additional manual cookie clearing - attempt to help the browser
    document.cookie.split(';').forEach(function(cookie) {
      const name = cookie.trim().split('=')[0];
      // Set expired date to clear the cookie
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
    });
  } catch (error) {
    console.error('❌ Logout error:', error);
    logoutSuccess = false;
  } finally {
    // Always clear client-side state regardless of server response
    clearClientState();
  }

  return logoutSuccess;
}

/**
 * Clear all client-side authentication state
 */
function clearClientState() {
  // Clear token lifetimes in localStorage
  clearTokenLifetimes();

  // Clear saved auth state
  clearAuthState();

  // Clear user state
  userStore.set(null);

  // Clear CSRF tokens
  csrfTokens = { access: null, refresh: null };

  // This will redirect to login page on next check
  console.log('✅ Client-side auth state cleared successfully');
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
      body: JSON.stringify({ username, password }),
      credentials: 'include' // Include cookies in the request
    });

    if (response.status === 401) {
      return { success: false, error: 'Invalid username or password' };
    } else if (!response.ok) {
      const error = await response.json();
      throw new Error(error.msg || 'Authentication error');
    }

    // Update CSRF tokens after login
    updateCsrfTokens();

    // Parse the response to get user info
    const data = await response.json();

    // Save token lifetimes from response
    if (data && data.token_lifetime) {
      const tokenLifetime = data.token_lifetime;
      const refreshTokenLifetime = data.refresh_token_lifetime;
      saveTokenLifetimes(tokenLifetime, refreshTokenLifetime);
    }

    // Update user store with user ID
    if (data && data.user) {
      userStore.set({ id: data.user.id });
      saveAuthState(data.user.id);
    }

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

/**
 * Save user ID to local storage for potential restoration
 * @param {string} userId - User ID to save
 */
export function saveAuthState(userId) {
  if (!userId) return;

  localStorage.setItem('auth_state', JSON.stringify({
    userId: userId,
    timestamp: Date.now()
  }));
  console.log('Auth state saved for user:', userId);
}

/**
 * Try to restore auth state from local storage
 * @returns {Object|null} - Restored auth state or null
 */
export function restoreAuthState() {
  try {
    const savedState = localStorage.getItem('auth_state');
    if (!savedState) return null;

    const state = JSON.parse(savedState);

    // Check if saved state is still valid (30 days)
    const maxAge = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds
    if (Date.now() - state.timestamp > maxAge) {
      localStorage.removeItem('auth_state');
      return null;
    }

    console.log('Restored auth state for user:', state.userId);
    return state;
  } catch (error) {
    console.error('Error restoring auth state:', error);
    clearAuthState();
    return null;
  }
}

/**
 * Clear saved auth state from local storage
 */
export function clearAuthState() {
  localStorage.removeItem('auth_state');
  console.log('Auth state cleared');
}