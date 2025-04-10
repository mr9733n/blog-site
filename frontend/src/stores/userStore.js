import { writable, derived } from 'svelte/store';
import { API_URL, AUTH_SETTINGS } from '../config';

// Time threshold for inactivity
export const INACTIVITY_THRESHOLD = AUTH_SETTINGS.INACTIVITY_THRESHOLD;
let lastUserActivity = Date.now();

// Loading state for token refresh operations
export const tokenRefreshLoading = writable(false);

// Initial user state (null until auth check)
export const userStore = writable(null);

// User activity tracking
export function updateUserActivity() {
  lastUserActivity = Date.now();
}

export function maskEmail(email) {
  if (!email) return '';
  const [username, domain] = email.split('@');

  let maskedUsername;
  if (username.length <= 4) {
    maskedUsername = username.charAt(0) + '*'.repeat(username.length - 2) + username.charAt(username.length - 1);
  } else {
    maskedUsername = username.slice(0, 2) + '*'.repeat(username.length - 4) + username.slice(-2);
  }

  let maskedDomain;
  if (domain.length <= 4) {
    maskedDomain = domain.charAt(0) + '*'.repeat(domain.length - 2) + domain.charAt(domain.length - 1);
  } else {
    maskedDomain = domain.slice(0, 2) + '*'.repeat(domain.length - 4) + domain.slice(-2);
  }

  return `${maskedUsername}@${maskedDomain}`;
}

// Export the current user activity timestamp for use in other modules
export function getLastUserActivity() {
  return lastUserActivity;
}

// Helper function to get token lifetime from cookie
function getTokenLifetime() {
  // First check localStorage (your existing approach)
  const storedTokenLifetime = localStorage.getItem('tokenLifetime');
  if (storedTokenLifetime) {
    return parseInt(storedTokenLifetime, 10);
  }

  // Fallback to cookie method (for backward compatibility)
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'token_lifetime') {
      return parseInt(value, 10);
    }
  }

  return 1800; // Default to 30 minutes if not found
}

// Derived store for token expiration countdown
export const tokenExpiration = derived(
  userStore,
  ($userStore, set) => {
    // Get initial token lifetime
    let remainingSeconds = getTokenLifetime();

    const updateExpiration = () => {
      if (!$userStore) {
        set(0);
        return;
      }

      if (remainingSeconds <= 0) {
        set(0);
        return;
      }

      // Decrement by 1 second
      remainingSeconds--;
      set(remainingSeconds);
    };

    // Initial update
    updateExpiration();

    // Setup interval to update countdown every second
    const interval = setInterval(updateExpiration, 1000);

    // Cleanup on unsubscribe
    return () => clearInterval(interval);
  }
);