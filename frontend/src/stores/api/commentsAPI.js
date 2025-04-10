import { API_URL } from '../../config';
import { authFetch } from '../authService';
import { debugApiCall } from './apiUtils';


export const commentsAPI = {
  // Get post comments
  getPostComments: debugApiCall('/posts/:id/comments', async function(postId) {
    try {
      const response = await fetch(`${API_URL}/posts/${postId}/comments`, {
      credentials: 'include'  // Add this
    });

      if (!response.ok) {
        throw new Error('Error loading comments');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching comments:', error);
      return [];
    }
  }),

    // Add comment
  addComment: debugApiCall('/posts/:postId/comments', async function(postId, content) {
    try {
      const response = await authFetch(`${API_URL}/posts/${postId}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
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
        credentials: 'include',
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
        method: 'DELETE',
        credentials: 'include',
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

};