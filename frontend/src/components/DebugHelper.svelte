<!-- DebugHelper.svelte -->
<script>
  import { API_URL } from '../config';
  import { userStore } from '../stores/userStore';
  import { authFetch, getCsrfToken, updateCsrfTokens } from '../stores/authService';

  let showDebug = false;
  let debugInfo = {};
  let user;

  userStore.subscribe(value => {
    user = value;
  });

  function toggleDebug() {
    showDebug = !showDebug;
    if (showDebug) {
      checkAdminStatus();
    }
  }

  function checkAdminStatus() {
    debugInfo = {};

    // Update CSRF tokens
    updateCsrfTokens();

    // Get user ID and type
    if (user) {
      debugInfo.userId = user.id;
      debugInfo.userIdType = typeof user.id;
      debugInfo.isAdminCheck = String(user.id) === '1';
    } else {
      debugInfo.userError = 'No user object found';
    }

    // Get current cookies
    try {
      const cookies = document.cookie.split(';')
        .map(cookie => cookie.trim())
        .reduce((acc, cookie) => {
          const [name, value] = cookie.split('=');
          acc[name] = value;
          return acc;
        }, {});

      debugInfo.cookies = cookies;

      // Add CSRF tokens specifically
      debugInfo.csrfTokens = {
        access: getCsrfToken('access'),
        refresh: getCsrfToken('refresh')
      };
    } catch (error) {
      debugInfo.cookieError = error.message;
    }
  }

  async function testRequest(endpoint, method = 'GET', data = null) {
    try {
      const options = {
        method: method,
        credentials: 'include',
        headers: {} // Initialize headers properly
      };

      // Add Content-Type for requests with body
      if (data && (method === 'POST' || method === 'PUT')) {
        options.headers['Content-Type'] = 'application/json';

        // Add appropriate CSRF token for the endpoint
        const tokenType = endpoint === '/refresh' ? 'refresh' : 'access';
        const csrfToken = getCsrfToken(tokenType);

        if (csrfToken) {
          options.headers['X-CSRF-TOKEN'] = csrfToken;
        }

        options.body = JSON.stringify(data);
      }

      const response = await authFetch(`${API_URL}${endpoint}`, options);

      let result = {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: {},
        csrfToken: endpoint === '/refresh' ? getCsrfToken('refresh') : getCsrfToken('access')
      };

      // Save headers for analysis
      response.headers.forEach((value, name) => {
        result.headers[name] = value;
      });

      if (response.ok) {
        try {
          const data = await response.json();
          result.data = data;
        } catch (e) {
          result.parseError = 'Could not parse JSON response';
        }
      }

      return result;
    } catch (error) {
      return { error: error.message };
    }
  }

  async function checkEndpoints() {
    debugInfo.endpoints = {};

    // Update CSRF tokens before testing
    updateCsrfTokens();

    // Show current CSRF tokens
    debugInfo.currentCsrfTokens = {
      access: getCsrfToken('access'),
      refresh: getCsrfToken('refresh')
    };

    // Check user endpoint
    debugInfo.endpoints.me = await testRequest('/me', 'GET');

    // Add a small delay to prevent race conditions
    await new Promise(resolve => setTimeout(resolve, 300));

    // Check refresh endpoint with refresh CSRF token
    debugInfo.endpoints.refresh = await testRequest('/refresh', 'POST');
  }
</script>

{#if showDebug}
  <div class="debug-panel">
    <button class="close-btn" on:click={toggleDebug}>Close Debug</button>

    <h3>Debug Information</h3>

    <div class="debug-section">
      <h4>User and Admin Status</h4>
      <pre>{JSON.stringify(user, null, 2)}</pre>

      <div class="debug-checks">
        <div>
          <span>User ID:</span>
          <span class="value">{debugInfo.userId !== undefined ? debugInfo.userId : 'undefined'}</span>
        </div>
        <div>
          <span>ID Type:</span>
          <span class="value">{debugInfo.userIdType || 'unknown'}</span>
        </div>
        <div>
          <span>Is Admin Check:</span>
          <span class="value {debugInfo.isAdminCheck ? 'success' : 'error'}">
            {debugInfo.isAdminCheck ? 'Yes' : 'No'}
          </span>
        </div>
      </div>

      <button class="debug-btn" on:click={checkAdminStatus}>Refresh Admin Status</button>
    </div>

    <div class="debug-section">
      <h4>Cookies and CSRF Tokens</h4>
      {#if debugInfo.cookies}
        <h5>All Cookies</h5>
        <pre>{JSON.stringify(debugInfo.cookies, null, 2)}</pre>

        {#if debugInfo.csrfTokens}
          <h5>CSRF Tokens</h5>
          <pre>{JSON.stringify(debugInfo.csrfTokens, null, 2)}</pre>
        {/if}
      {:else if debugInfo.cookieError}
        <p class="error">{debugInfo.cookieError}</p>
      {:else}
        <p>Click "Refresh Admin Status" to check cookies</p>
      {/if}
    </div>

    <div class="debug-section">
      <h4>API Endpoints</h4>
      <button class="debug-btn" on:click={checkEndpoints}>Test Endpoints</button>

      {#if debugInfo.endpoints}
        {#if debugInfo.currentCsrfTokens}
          <h5>Current CSRF Tokens</h5>
          <pre>{JSON.stringify(debugInfo.currentCsrfTokens, null, 2)}</pre>
        {/if}

        <div class="endpoints-result">
          <h5>/me Endpoint</h5>
          <pre>{JSON.stringify(debugInfo.endpoints.me, null, 2)}</pre>

          <h5>/refresh Endpoint</h5>
          <pre>{JSON.stringify(debugInfo.endpoints.refresh, null, 2)}</pre>
        </div>
      {/if}
    </div>
  </div>
{:else}
  <button class="debug-toggle" on:click={toggleDebug}>Debug</button>
{/if}

<style>
  .debug-panel {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 350px;
    max-height: 80vh;
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.15);
    z-index: 1000;
    overflow-y: auto;
    padding: 15px;
  }

  .debug-toggle {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 15px;
    cursor: pointer;
    z-index: 999;
  }

  .close-btn {
    background-color: #6c757d;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    cursor: pointer;
    margin-bottom: 10px;
  }

  .debug-section {
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid #dee2e6;
  }

  .debug-section h4 {
    margin: 10px 0;
    color: #495057;
  }

  .debug-section h5 {
    margin: 10px 0 5px 0;
    color: #6c757d;
    font-size: 0.9rem;
  }

  .debug-checks {
    background-color: #e9ecef;
    padding: 10px;
    border-radius: 4px;
    margin: 10px 0;
  }

  .debug-checks div {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
  }

  .value {
    font-weight: bold;
  }

  .success {
    color: #28a745;
  }

  .error {
    color: #dc3545;
  }

  .debug-btn {
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    cursor: pointer;
    font-size: 0.9rem;
    margin-top: 10px;
  }

  pre {
    background-color: #f1f3f5;
    padding: 8px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 0.8rem;
    margin: 10px 0;
  }

  .endpoints-result {
    margin-top: 15px;
  }
</style>