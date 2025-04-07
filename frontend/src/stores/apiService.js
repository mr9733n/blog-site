// src/stores/apiService.js
import { authFetch } from './authService';
import { API_URL } from '../config';

let pendingPostsRequest = null;
let pendingPostsTimeout = null;
const DEBUG = true;

// Request counter
let apiRequestCount = 0;

// Debug wrapper for all API calls
function debugApiCall(endpoint, fn) {
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

// All API functions grouped in a single exportable object
export const api = {
  // Get posts with pagination
  getPosts: debugApiCall('/posts', async function(limit = null, offset = null) {
    // If there's already a pending request, return it instead of creating a new one
    if (pendingPostsRequest) {
      console.log("Reusing existing posts request");
      return pendingPostsRequest;
    }

    console.log("Creating new posts request");
    try {
      let url = `${API_URL}/posts`;
      const params = new URLSearchParams();

      if (limit !== null) params.append('limit', limit);
      if (offset !== null) params.append('offset', offset);

      const queryString = params.toString();
      if (queryString) url += `?${queryString}`;

      // Create a new promise and store it
      pendingPostsRequest = (async () => {
        try {
          const response = await fetch(url);

          if (!response.ok) {
            throw new Error('Error loading posts');
          }

          const data = await response.json();
          return data;
        } catch (error) {
          console.error('Error fetching posts:', error);
          return [];
        } finally {
          // Clear the pending request after it completes (success or error)
          clearTimeout(pendingPostsTimeout);
          pendingPostsTimeout = setTimeout(() => {
            pendingPostsRequest = null;
          }, 500); // Increased delay to prevent immediate new requests
        }
      })();

      return pendingPostsRequest;
    } catch (error) {
      console.error('Error in getPosts:', error);
      pendingPostsRequest = null;
      return [];
    }
  }),
  // Get a single post
  getPost: debugApiCall('posts/:id', async function(id) {
    try {
      const response = await fetch(`${API_URL}/posts/${id}`);

      if (!response.ok) {
        throw new Error('Post not found');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching post:', error);
      throw error;
    }
  }),

  // Get user's posts
  getUserPosts: debugApiCall('/users/:id/posts', async function(userId) {
    try {
      const response = await fetch(`${API_URL}/users/${userId}/posts`);

      if (!response.ok) {
        throw new Error('Error loading user posts');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching user posts:', error);
      return [];
    }
  }),

  // Get current user info
  getCurrentUser: debugApiCall('/me', async function() {
    try {
      const response = await authFetch(`${API_URL}/me`);

      if (!response.ok) {
        throw new Error('Error loading user information');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching current user:', error);
      throw error;
    }
  }),

  // Comments API

  // Get post comments
  getPostComments: debugApiCall('/posts/:id/comments', async function(postId) {
    try {
      const response = await fetch(`${API_URL}/posts/${postId}/comments`);

      if (!response.ok) {
        throw new Error('Error loading comments');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching comments:', error);
      return [];
    }
  }),

  // Get saved posts
  getSavedPosts: debugApiCall('/saved/posts', async function() {
    try {
      const response = await authFetch(`${API_URL}/saved/posts`);

      if (!response.ok) {
        throw new Error('Error loading saved posts');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching saved posts:', error);
      return [];
    }
  }),

  // Check if post is saved
  isPostSaved: debugApiCall('/posts/:postId/is_saved', async function(postId) {
    try {
      const response = await authFetch(`${API_URL}/posts/${postId}/is_saved`);

      if (!response.ok) {
        throw new Error('Error checking if post is saved');
      }

      const data = await response.json();
      return data.is_saved;
    } catch (error) {
      console.error('Error checking if post is saved:', error);
      return false;
    }
  }),

  // Get post images
  getPostImages: debugApiCall('/posts/:postId/images', async function(postId) {
    try {
      const response = await fetch(`${API_URL}/posts/${postId}/images`);

      if (!response.ok) {
        throw new Error('Error getting images');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching post images:', error);
      return [];
    }
  }),

  // Get user images
  getUserImages: debugApiCall('/users/:userId/images', async function(userId, limit = null) {
    try {
      let url = `${API_URL}/users/${userId}/images`;

      if (limit) {
        url += `?limit=${limit}`;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('Error getting user images');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching user images:', error);
      return [];
    }
  }),

  // Admin functions

  // Get all users (admin only)
  getAllUsers: debugApiCall('/admin/users', async function() {
    try {
      const response = await authFetch(`${API_URL}/admin/users`);

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Insufficient privileges');
        }
        throw new Error('Error getting user list');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching all users:', error);
      throw error;
    }
  }),

  // Get user details (admin only)
  getUserDetails: debugApiCall('/admin/users/:userId', async function(userId) {
    try {
      const response = await authFetch(`${API_URL}/admin/users/${userId}`);

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Insufficient privileges');
        } else if (response.status === 404) {
          throw new Error('User not found');
        }
        throw new Error('Error getting user data');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching user details:', error);
      throw error;
    }
  }),

  // Post management functions

  // Create post
  createPost: debugApiCall('/posts', async function(title, content) {
    try {
      console.log('Creating post with data:', { title, content });

      const response = await authFetch(`${API_URL}/posts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title, content })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error creating post');
      }

      return await response.json();
    } catch (error) {
      console.error('Error creating post:', error);
      throw error;
    }
  }),

  // Update post
  updatePost: debugApiCall('/posts/:id', async function(id, title, content) {
    try {
      const response = await authFetch(`${API_URL}/posts/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title, content })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error updating post');
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating post:', error);
      throw error;
    }
  }),

  // Delete post
  deletePost: debugApiCall('/posts/:id', async function(id) {
    try {
      const response = await authFetch(`${API_URL}/posts/${id}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error deleting post');
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting post:', error);
      throw error;
    }
  }),

  // Comment management functions

  // Add comment
  addComment: debugApiCall('/posts/:postId/comments', async function(postId, content) {
    try {
      const response = await authFetch(`${API_URL}/posts/${postId}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error adding comment');
      }

      return await response.json();
    } catch (error) {
      console.error('Error adding comment:', error);
      throw error;
    }
  }),

  // Update comment
  updateComment: debugApiCall('/comments/:commentId', async function(commentId, content) {
    try {
      const response = await authFetch(`${API_URL}/comments/${commentId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error updating comment');
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating comment:', error);
      throw error;
    }
  }),

  // Delete comment
  deleteComment: debugApiCall('/comments/:commentId', async function(commentId) {
    try {
      const response = await authFetch(`${API_URL}/comments/${commentId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error deleting comment');
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting comment:', error);
      throw error;
    }
  }),

  // Token settings
  updateTokenSettings: debugApiCall('/settings/token-settings', async function(tokenLifetime, refreshTokenLifetime) {
    try {
      const response = await authFetch(`${API_URL}/settings/token-settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          token_lifetime: tokenLifetime,
          refresh_token_lifetime: refreshTokenLifetime
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error updating settings');
      }

      const result = await response.json();

      // Save new tokens
      if (result.access_token) {
        localStorage.setItem('authToken', result.access_token);
        localStorage.setItem('refreshToken', result.refresh_token);
        console.log('Tokens updated with new lifetime settings');
      }

      return result;
    } catch (error) {
      console.error('Error updating token settings:', error);
      throw error;
    }
  }),

  // Post saving
  savePost: debugApiCall('/posts/:postId/save', async function(postId) {
    try {
      const response = await authFetch(`${API_URL}/posts/${postId}/save`, {
        method: 'POST'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error saving post');
      }

      return await response.json();
    } catch (error) {
      console.error('Error saving post:', error);
      throw error;
    }
  }),

  unsavePost: debugApiCall('/posts/:postId/unsave', async function(postId) {
    try {
      const response = await authFetch(`${API_URL}/posts/${postId}/unsave`, {
        method: 'POST'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error removing post from saved');
      }

      return await response.json();
    } catch (error) {
      console.error('Error unsaving post:', error);
      throw error;
    }
  }),

  // Image operations
  uploadImage: debugApiCall('/images/upload', async function(file, postId = null) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      if (postId) {
        formData.append('post_id', postId);
      }

      const response = await authFetch(`${API_URL}/images/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        // Check response content type
        const contentType = response.headers.get('content-type');

        if (contentType && contentType.includes('application/json')) {
          // If JSON, parse normally
          const error = await response.json();
          throw new Error(error.msg || 'Error uploading image');
        } else {
          // If not JSON (e.g. HTML), show more friendly message
          if (response.status === 413) {
            throw new Error('File too large. Maximum size is 5 MB');
          } else {
            // For other errors show status code
            throw new Error(`Server error (${response.status}). Try a smaller file or different format.`);
          }
        }
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading image:', error);
      throw error;
    }
  }),

  deleteImage: debugApiCall('/images/:imageId', async function(imageId) {
    try {
      const response = await authFetch(`${API_URL}/images/${imageId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error deleting image');
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting image:', error);
      throw error;
    }
  }),

  attachImageToPost: debugApiCall('/images/:imageId/post/:postId', async function(imageId, postId) {
    try {
      const response = await authFetch(`${API_URL}/images/${imageId}/post/${postId}`, {
        method: 'PUT'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error attaching image to post');
      }

      return await response.json();
    } catch (error) {
      console.error('Error attaching image to post:', error);
      throw error;
    }
  }),

  detachImageFromPost: debugApiCall('/images/:imageId/post', async function(imageId) {
    try {
      const response = await authFetch(`${API_URL}/images/${imageId}/post`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error detaching image from post');
      }

      return await response.json();
    } catch (error) {
      console.error('Error detaching image from post:', error);
      throw error;
    }
  }),

  // Admin functions
  toggleUserBlock: debugApiCall('/admin/users/:userId/block', async function(userId, blockStatus) {
    try {
      const response = await authFetch(`${API_URL}/admin/users/${userId}/block`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ blocked: blockStatus })
      });

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Insufficient privileges');
        }
        const error = await response.json();
        throw new Error(error.msg || 'Error changing user block status');
      }

      return await response.json();
    } catch (error) {
      console.error('Error toggling user block status:', error);
      throw error;
    }
  }),

  updateUserData: debugApiCall('/admin/users/:userId', async function(userId, userData) {
    try {
      const response = await authFetch(`${API_URL}/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
      });

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Insufficient privileges');
        }
        const error = await response.json();
        throw new Error(error.msg || 'Error updating user data');
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating user data:', error);
      throw error;
    }
  })
};