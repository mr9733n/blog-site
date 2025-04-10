// src/stores/api/postsAPI.js
import { API_URL } from '../../config';
import { authFetch } from '../authService';
import { debugApiCall } from './apiUtils';

let pendingPostsRequest = null;
let pendingPostsTimeout = null;

export const postsAPI = {
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
		const response = await fetch(url, {
		  credentials: 'include'  // Add this to all fetch requests
		});
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
  getPost: debugApiCall('/posts/:id', async function(id) {
    try {
      const response = await fetch(`${API_URL}/posts/${id}`, {
      credentials: 'include'  // Add this
    });

      if (!response.ok) {
        throw new Error('Post not found');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching post:', error);
      throw error;
    }
  }),

  // Create post
  createPost: debugApiCall('/posts', async function(title, content) {
    try {
      console.log('Creating post with data:', { title, content });

      const response = await authFetch(`${API_URL}/posts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
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
        credentials: 'include',
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
        method: 'DELETE',
        credentials: 'include',
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

  // Post saving
  savePost: debugApiCall('/posts/:postId/save', async function(postId) {
    try {
      const response = await authFetch(`${API_URL}/posts/${postId}/save`, {
        method: 'POST',
        credentials: 'include',
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
        method: 'POST',
        credentials: 'include',
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

  // Get saved posts
  getSavedPosts: debugApiCall('/saved/posts', async function() {
    try {
      const response = await authFetch(`${API_URL}/saved/posts`, {
      credentials: 'include'  // Add this
    });

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
      const response = await authFetch(`${API_URL}/posts/${postId}/is_saved`, {
      credentials: 'include'  // Add this
    });

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
      const response = await fetch(`${API_URL}/posts/${postId}/images`, {
      credentials: 'include'  // Add this
    });

      if (!response.ok) {
        throw new Error('Error getting images');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching post images:', error);
      return [];
    }
  }),
};