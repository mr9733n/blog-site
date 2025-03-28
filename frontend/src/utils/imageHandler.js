// src/utils/imageHandler.js

/**
 * Validates if a URL is accessible before using it
 * @param {string} url - The URL to check
 * @returns {Promise<boolean>} - Whether the URL is accessible
 */
export async function validateImageUrl(url) {
  try {
    const response = await fetch(url, { method: 'HEAD' });
    return response.ok;
  } catch (error) {
    console.error('Error validating image URL:', error);
    return false;
  }
}

/**
 * Processes an image URL from the API to ensure it's properly formatted
 * @param {string} apiPath - The path from the API
 * @returns {string} - A correctly formatted image URL
 */
export function processImageUrl(apiPath) {
  if (!apiPath) return '';

  // Remove any leading slashes to prevent double slashes
  const cleanPath = apiPath.startsWith('/') ? apiPath.substring(1) : apiPath;

  // Build the complete URL with the base URL
  // Using window.location.origin ensures we're using the same domain
  return `${window.location.origin}/${cleanPath}`;
}