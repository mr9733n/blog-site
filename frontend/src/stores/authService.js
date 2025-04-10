// src/stores/authService.js
import { userStore, tokenRefreshLoading, getLastUserActivity, INACTIVITY_THRESHOLD } from './userStore';
import { API_URL } from '../config';
import { getCsrfTokenFromCookies, getAllCsrfTokens } from '../utils/csrfUtils';

// Last token refresh timestamp to prevent too frequent refresh attempts
let lastRefreshAttempt = 0;
let csrfTokens = { access: null, refresh: null };
const MIN_REFRESH_INTERVAL = 5000; // 5 seconds minimum between refresh attempts
const AUTH_STATE_KEY = 'auth_state';
const TOKEN_LIFETIME_KEY = 'tokenLifetime';
const REFRESH_TOKEN_LIFETIME_KEY = 'refreshTokenLifetime';
let authInitialized = false;

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
    const hasCsrfTokens = updateCsrfTokens();
    const hasAccessToken = !!hasCsrfTokens.access;
    const hasRefreshToken = !!hasCsrfTokens.refresh;

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
 * With cookie-based auth, we don't need to manually add tokens
 *
 * @param {string} url - API URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} - Fetch response
 */
export async function authFetch(url, options = {}) {
  // Make sure we have the latest CSRF tokens
  updateCsrfTokens();

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
 * Check if user is authenticated with the server
 * @returns {Promise<boolean>} - True if authenticated
 */
export async function isAuthenticated() {
  try {
    console.log('🔍 Checking authentication with server');
    const response = await fetch(`${API_URL}/me`, {
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
      if (data && data.user && data.user.id) {
        // Update user store and save state
        userStore.set({ id: data.user.id });
        saveAuthState(data.user.id);
        console.log(`✅ Authentication confirmed for user: ${data.user.id}`);
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
      },
      cache: 'no-store' // Prevent caching
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

    // Get the latest access CSRF token
    const accessCsrfToken = getCsrfToken('access');

    // Call logout endpoint to clear server-side cookies
    const response = await fetch(`${API_URL}/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-TOKEN': accessCsrfToken
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

  // Reset CSRF tokens
  csrfTokens = { access: null, refresh: null };
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

  // Clear CSRF tokens
  csrfTokens = { access: null, refresh: null };
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

    const response = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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
    const maxAge = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds
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