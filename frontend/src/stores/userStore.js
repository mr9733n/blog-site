import { writable, derived } from 'svelte/store';
import { API_URL, AUTH_SETTINGS } from '../config';

// Time threshold for inactivity
export const INACTIVITY_THRESHOLD = AUTH_SETTINGS.INACTIVITY_THRESHOLD;
let lastUserActivity = Date.now();

// Loading state for token refresh operations
export const tokenRefreshLoading = writable(false);

// Check for token in localStorage during initialization
const storedToken = typeof localStorage !== 'undefined' ? localStorage.getItem('authToken') : null;
let initialUser = null;

// Helper function to validate token and extract user info
export function isTokenExpired(token, bufferSeconds = 0) {
  if (!token) return true;

  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(window.atob(base64));

    // Check with buffer for preemptive renewal
    return payload.exp * 1000 <= Date.now() + (bufferSeconds * 1000);
  } catch (e) {
    console.error('Error checking token expiration', e);
    return true;
  }
}

// Initialize user from stored token if valid
if (storedToken) {
  if (!isTokenExpired(storedToken)) {
    try {
      const base64Url = storedToken.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(window.atob(base64));
      initialUser = { id: payload.sub };
    } catch (e) {
      console.error('Error reading token', e);
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem('authToken');
      }
    }
  } else {
    // Token expired, remove it
    console.log('Token expired, removing');
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('authToken');
    }
  }
}

// Create store with initial value
export const userStore = writable(initialUser);

// Derived store for token expiration countdown
export const tokenExpiration = derived(
  userStore,
  ($userStore, set) => {
    const checkExpiration = () => {
      const token = typeof localStorage !== 'undefined' ? localStorage.getItem('authToken') : null;
      if (!token) return set(0);

      try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(window.atob(base64));
        set(Math.max(0, Math.floor(payload.exp - Date.now()/1000)));
      } catch (e) {
        console.error('Error checking token', e);
        set(0);
      }
    };

    // Initial check
    checkExpiration();

    // Setup interval
    const interval = setInterval(checkExpiration, 1000);

    // Cleanup on unsubscribe
    return () => clearInterval(interval);
  }
);

// User activity tracking
export function updateUserActivity() {
  lastUserActivity = Date.now();
}

// Export the current user activity timestamp for use in other modules
export function getLastUserActivity() {
  return lastUserActivity;
}