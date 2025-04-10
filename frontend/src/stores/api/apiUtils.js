// src/stores/api/apiUtils.js
const DEBUG = true;
let apiRequestCount = 0;

// Debug wrapper for all API calls
export function debugApiCall(endpoint, fn) {
  return async function(...args) {
    apiRequestCount++;

    if (DEBUG) {
      console.log(`[API Call #${apiRequestCount}] ${endpoint}`, {
        time: new Date().toISOString(),
        args: args.length > 0 ? args : 'none'
      });
    }

    // Log excessive requests
    if (apiRequestCount % 10 === 0) {
      console.warn(`⚠️ Warning: ${apiRequestCount} API requests made`);
    }

    try {
      const result = await fn.apply(this, args);

      if (DEBUG) {
        console.log(`[API Response #${apiRequestCount}] ${endpoint}`, {
          success: true,
          time: new Date().toISOString()
        });
      }

      return result;
    } catch (error) {
      console.error(`[API Error #${apiRequestCount}] ${endpoint}`, {
        error: error.message,
        time: new Date().toISOString()
      });

      throw error;
    }
  };
}