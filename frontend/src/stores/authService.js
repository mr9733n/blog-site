// src/stores/authService.js
import { userStore, tokenRefreshLoading, getLastUserActivity, INACTIVITY_THRESHOLD } from './userStore';
import { API_URL } from '../config';
import { getCsrfTokenFromCookies, getAllCsrfTokens, getCsrfStateFromCookies, getAllCsrfData } from '../utils/csrfUtils';
import { getDeviceFingerprint } from '../utils/fingerprintUtils';

// Last token refresh timestamp to prevent too frequent refresh attempts
let lastRefreshAttempt = 0;
let csrfData = { access: null, refresh: null, state: null };
const MIN_REFRESH_INTERVAL = 5000; // 5 seconds minimum between refresh attempts
const AUTH_STATE_KEY = 'auth_state';
const TOKEN_LIFETIME_KEY = 'tokenLifetime';
const REFRESH_TOKEN_LIFETIME_KEY = 'refreshTokenLifetime';
let authInitialized = false;

// Update CSRF tokens and state (called at login and refresh)
export function updateCsrfData() {
  csrfData = getAllCsrfData();
  return csrfData;
}

// Get current CSRF token based on type
export function getCsrfToken(type = 'access') {
  if (!csrfData.access && !csrfData.refresh) {
    updateCsrfData();
  }

  return type === 'refresh' ? csrfData.refresh : csrfData.access;
}

// Get current CSRF state
export function getCsrfState() {
  if (!csrfData.state) {
    updateCsrfData();
  }

  return csrfData.state;
}

// Save token lifetimes to localStorage
export function saveTokenLifetimes(tokenLifetime, refreshTokenLifetime) {
  if (tokenLifetime) {
    localStorage.setItem(TOKEN_LIFETIME_KEY, tokenLifetime.toString());
  }
  if (refreshTokenLifetime) {
    localStorage.setItem(REFRESH_TOKEN_LIFETIME_KEY, refreshTokenLifetime.toString());
  }
}

// Clear token lifetimes from localStorage
export function clearTokenLifetimes() {
  localStorage.removeItem(TOKEN_LIFETIME_KEY);
  localStorage.removeItem(REFRESH_TOKEN_LIFETIME_KEY);
}

/**
 * Initialize authentication state on app load
 * This should be called once when the app loads
 */
export async function initAuth() {
  if (authInitialized) return;

  console.log('🔐 Initializing authentication state');

  try {
    // First check if we have cookies that might indicate an active session
    const csrfData = updateCsrfData();
    const hasAccessToken = !!csrfData.access;
    const hasRefreshToken = !!csrfData.refresh;

    console.log(`Found tokens - Access: ${hasAccessToken}, Refresh: ${hasRefreshToken}`);

    // Next check if we have stored auth state
    const savedState = restoreAuthState();

    if (savedState && savedState.userId) {
      console.log(`Found saved auth state for user: ${savedState.userId}`);

      // Temporarily update the user store with the saved ID
      userStore.set({ id: savedState.userId });

      // Verify with server if this session is actually valid
      const authenticated = await isAuthenticated();

      if (!authenticated) {
        console.log('Server rejected authentication, clearing local state');
        clearAllClientState();
      } else {
        console.log('Server confirmed authentication, session is valid');
      }
    } else if (hasAccessToken || hasRefreshToken) {
      // We have cookies but no saved state, try to verify/refresh tokens
      console.log('Found auth cookies but no saved state, checking with server');
      const authenticated = await isAuthenticated();

      if (!authenticated) {
        // Try refresh as a last resort
        const refreshed = await refreshToken();
        if (!refreshed) {
          console.log('Authentication failed and refresh failed, clearing state');
          clearAllClientState();
        }
      }
    }
  } catch (error) {
    console.error('Auth initialization error:', error);
    clearAllClientState();
  } finally {
    authInitialized = true;
  }
}

/**
 * Helper function for authenticated requests
 * With cookie-based auth, properly handling CSRF tokens
 *
 * @param {string} url - API URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} - Fetch response
 */
export async function authFetch(url, options = {}) {
  console.log(`🔐 Auth fetch for ${url}`);

  // Make sure we have the latest CSRF tokens and state
  const { access: csrfToken, refresh: refreshToken, state: csrfState } = updateCsrfData();

  // Include credentials to ensure cookies are sent
  const fetchOptions = {
    ...options,
    credentials: 'include'
  };

  // Configure headers
  fetchOptions.headers = {
    ...fetchOptions.headers || {}
  };

  // Add device fingerprint to all requests
  try {
    const deviceFingerprint = await getDeviceFingerprint();
    fetchOptions.headers['X-Device-Fingerprint'] = deviceFingerprint;
  } catch (error) {
    console.warn('Could not generate device fingerprint:', error);
  }

  // Add the appropriate CSRF token and state based on the endpoint
  if (options.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method)) {
    console.log(`Adding CSRF headers for ${options.method} request to ${url}`);

    // Add CSRF state to all protected requests if available
    if (csrfState) {
      console.log(`Adding CSRF state: ${csrfState.substring(0, 8)}...`);
      fetchOptions.headers['X-CSRF-STATE'] = csrfState;
    } else {
      console.warn('No CSRF state available for protected request');
    }

    // Use refresh token for refresh endpoint
    if (url.endsWith('/refresh')) {
      if (refreshToken) {
        console.log(`Adding refresh CSRF token: ${refreshToken.substring(0, 8)}...`);
        fetchOptions.headers['X-CSRF-TOKEN'] = refreshToken;
      } else {
        console.warn('No refresh CSRF token available for refresh request');
      }
    } else if (csrfToken) {
      // Use access token for all other endpoints
      console.log(`Adding access CSRF token: ${csrfToken.substring(0, 8)}...`);
      fetchOptions.headers['X-CSRF-TOKEN'] = csrfToken;
    } else {
      console.warn('No access CSRF token available for protected request');
    }
  }

  try {
    // Try the fetch with current auth cookie
    const response = await fetch(url, fetchOptions);

    // Проверяем заголовки ответа на наличие новых CSRF токенов
    const responseHeaders = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });
    console.log('Response headers:', responseHeaders);

    // Update CSRF tokens if provided in response headers
    const newCsrfToken = response.headers.get('X-CSRF-TOKEN');
    if (newCsrfToken) {
      console.log('Received new CSRF token in response');
      // We can't know which token was updated, so update both from cookies
      updateCsrfData();
    }

    // Handle auth errors - if we get a 401 or 403, try to refresh token once
    if (response.status === 401 || response.status === 403) {
      console.log(`⏳ Auth error (${response.status}) for ${url}. Attempting refresh...`);

      // Try to refresh the token first
      const refreshSuccess = await refreshToken();

      if (!refreshSuccess) {
        console.warn('⚠️ Refresh failed');

        // Check for inactivity
        const now = Date.now();
        const lastUserActivity = getLastUserActivity();
        const inactiveTime = now - lastUserActivity;

        if (inactiveTime > INACTIVITY_THRESHOLD) {
          console.warn(`⏳ Inactive for ${inactiveTime / 1000} seconds — logging out.`);
          await logout(true);
          throw new Error('Session ended due to inactivity.');
        }

        console.warn('⚠️ Logging out due to auth failure after refresh attempt');
        await logout(true);
        throw new Error('Session expired. Please log in again.');
      }

      // After successful token refresh, update the CSRF tokens again
      const { access: newAccessToken, refresh: newRefreshToken, state: newCsrfState } = updateCsrfData();

      // Update headers with new CSRF data
      if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method)) {
        if (newCsrfState) {
          fetchOptions.headers['X-CSRF-STATE'] = newCsrfState;
        }

        if (url.endsWith('/refresh') && newRefreshToken) {
          fetchOptions.headers['X-CSRF-TOKEN'] = newRefreshToken;
        } else if (newAccessToken) {
          fetchOptions.headers['X-CSRF-TOKEN'] = newAccessToken;
        }
      }

      console.log('✅ Retrying request after successful token refresh');
      // Retry the original request with the new tokens
      return fetch(url, fetchOptions);
    }

    return response;
  } catch (error) {
    console.error('❌ Fetch error:', error);
    throw error;
  }
}

/**
 * Check if user is authenticated with the server
 * @returns {Promise<boolean>} - True if authenticated
 */
export async function isAuthenticated() {
  try {
    console.log('🔍 Checking authentication with server');
    const response = await authFetch(`${API_URL}/me`, {
      method: 'GET',
      credentials: 'include', // Include cookies
      cache: 'no-store' // Prevent caching
    });

    if (!response.ok) {
      console.log(`❌ Authentication check failed: ${response.status}`);
      return false;
    }

    // Try to get user info from response
    try {
      const data = await response.json();
      if (data && data.id) {
        // Update user store and save state
        userStore.set({ id: data.id });
        saveAuthState(data.id);
        console.log(`✅ Authentication confirmed for user: ${data.id}`);
      }
    } catch (e) {
      // If we can't parse JSON but response was OK, still consider authenticated
      console.warn('Could not parse user data from /me, but auth is valid');
    }

    return true;
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

    // Проверяем, не выполняется ли уже обновление
    const isRefreshing = await new Promise(resolve => {
      const unsubscribe = tokenRefreshLoading.subscribe(value => {
        resolve(value);
        unsubscribe();
      });
    });

    if (isRefreshing) {
      console.log('Another refresh is already in progress, waiting for it to complete');

      return new Promise(resolve => {
        const interval = setInterval(() => {
          tokenRefreshLoading.subscribe(value => {
            if (!value) { // когда обновление завершено
              clearInterval(interval);
              resolve(true); // Возвращаем true вместо вызова isAuthenticated()
            }
          })();
        }, 100);
      });
    }

    return true; // Возвращаем true, если обновление уже было недавно
  }

  lastRefreshAttempt = now;
  console.log('🔄 Attempting token refresh at:', new Date(now).toISOString());

  // Get the latest refresh CSRF token and state
  updateCsrfData();
  const refreshCsrfToken = getCsrfToken('refresh');
  const csrfState = getCsrfState();

  if (!refreshCsrfToken) {
    console.error('❌ No refresh CSRF token available');
    return false;
  }

  try {
    // Set loading state
    tokenRefreshLoading.set(true);

    // Get device fingerprint for the request
    const deviceFingerprint = await getDeviceFingerprint();

    // Используем явные заголовки для рефреша
    const headers = {
      'X-CSRF-TOKEN': refreshCsrfToken,
      'X-Device-Fingerprint': deviceFingerprint
    };

    // Добавляем CSRF-STATE, если он доступен
    if (csrfState) {
      headers['X-CSRF-STATE'] = csrfState;
    }

    const response = await fetch(`${API_URL}/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: headers,
      cache: 'no-store' // Prevent caching
    });

    // Если ответ не ok, логируем ошибку подробнее
    if (!response.ok) {
      console.error('Token refresh failed with status:', response.status);
      console.error('Response headers:',
        Array.from(response.headers.entries()).reduce((obj, [key, val]) => {
          obj[key] = val;
          return obj;
        }, {})
      );

      // Попытка получить текст ошибки
      const errorText = await response.text();
      console.error('Error response:', errorText);

      throw new Error(`Failed to refresh token: ${response.status} ${response.statusText}`);
    }

    // Update CSRF tokens after refresh
    updateCsrfData();

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
        saveAuthState(data.user.id);
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
    // Ensure tokenRefreshLoading is set to false when done
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
    console.log('🚪 Logging out user');

    // Get the latest access CSRF token and state
    const accessCsrfToken = getCsrfToken('access');
    const csrfState = getCsrfState();
    const deviceFingerprint = await getDeviceFingerprint();

    // Call logout endpoint to clear server-side cookies
    const response = await fetch(`${API_URL}/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-TOKEN': accessCsrfToken,
        'X-Device-Fingerprint': deviceFingerprint,
        ...(csrfState ? { 'X-CSRF-STATE': csrfState } : {})
      },
      cache: 'no-store' // Prevent caching
    });

    logoutSuccess = response.ok;

    if (logoutSuccess) {
      console.log('✅ Server confirmed logout');
    } else {
      console.warn(`⚠️ Server logout failed: ${response.status}`);
    }

    // Always clear cookies on the client side, regardless of server response
    clearAllCookies();
  } catch (error) {
    console.error('❌ Logout error:', error);
    logoutSuccess = false;
  } finally {
    // Always clear client-side state regardless of server response
    clearAllClientState();
    console.log('✅ Client-side logout complete');
  }

  return logoutSuccess;
}

/**
 * Clear all client-side cookies
 */
function clearAllCookies() {
  console.log('🧹 Clearing all cookies');

  // Get all cookies and clear them one by one
  document.cookie.split(';').forEach(function(cookie) {
    const name = cookie.trim().split('=')[0];
    if (!name) return;

    // Clear for root path
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;

    // Also try with domain
    const domain = window.location.hostname;
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=${domain}`;

    // Also try subdomain
    if (domain.indexOf('.') > 0) {
      const parentDomain = domain.substring(domain.indexOf('.'));
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=${parentDomain}`;
    }
  });

  // Reset CSRF data
  csrfData = { access: null, refresh: null, state: null };
}

/**
 * Clear all client-side authentication state
 */
function clearAllClientState() {
  console.log('🧹 Clearing all client-side auth state');

  // Clear token lifetimes in localStorage
  clearTokenLifetimes();

  // Clear saved auth state
  clearAuthState();

  // Clear user state
  userStore.set(null);

  // Clear CSRF data
  csrfData = { access: null, refresh: null, state: null };

  // Don't clear device fingerprint - it's device-specific, not session-specific
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

    // First ensure we're starting with a clean state
    clearAllClientState();

    // Get device fingerprint for the login
    const deviceFingerprint = await getDeviceFingerprint();

    const response = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Device-Fingerprint': deviceFingerprint
      },
      body: JSON.stringify({ username, password }),
      credentials: 'include', // Include cookies in the request
      cache: 'no-store' // Prevent caching
    });

    if (response.status === 401) {
      return { success: false, error: 'Invalid username or password' };
    } else if (!response.ok) {
      const error = await response.json();
      throw new Error(error.msg || 'Authentication error');
    }

    // Update CSRF data after login
    updateCsrfData();

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
    clearAllClientState(); // Clean up on error
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
      body: JSON.stringify({ username, email, password }),
      cache: 'no-store' // Prevent caching
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

  localStorage.setItem(AUTH_STATE_KEY, JSON.stringify({
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
    const savedState = localStorage.getItem(AUTH_STATE_KEY);
    if (!savedState) return null;

    const state = JSON.parse(savedState);

    // Check if saved state is still valid (30 days)
    const maxAge = 1 * 24 * 60 * 60 * 1000; // 1 day in milliseconds
    if (Date.now() - state.timestamp > maxAge) {
      localStorage.removeItem(AUTH_STATE_KEY);
      return null;
    }

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
  localStorage.removeItem(AUTH_STATE_KEY);
}