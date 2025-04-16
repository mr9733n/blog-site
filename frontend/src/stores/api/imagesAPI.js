import { API_URL } from '../../config';
import { authFetch } from '../authService';
import { debugApiCall } from './apiUtils';


export const imagesAPI = {
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
        credentials: 'include',
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
        method: 'DELETE',
        credentials: 'include',
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
        method: 'PUT',
        credentials: 'include',
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
        method: 'DELETE',
        credentials: 'include',
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

};