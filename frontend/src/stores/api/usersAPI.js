import { API_URL } from '../../config';
import { authFetch } from '../authService';
import { debugApiCall } from './apiUtils';


export const usersAPI = {

  // Get current user info
  getCurrentUser: debugApiCall('/me', async function() {
    try {
      const response = await authFetch(`${API_URL}/me`, {
      credentials: 'include'  // Add this
    });

      if (!response.ok) {
        throw new Error('Error loading user information');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching current user:', error);
      throw error;
    }
  }),

    // Update current user profile
  updateUserProfile: debugApiCall('/user/update', async function(userData) {
    try {
      const response = await authFetch(`${API_URL}/user/update`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(userData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.msg || 'Error updating profile');
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating profile:', error);
      throw error;
    }
  }),
    // Get user images
	getUserImages: debugApiCall('/users/:userId/images', async function(userId, limit = null) {
	  try {
		let url = `${API_URL}/users/${userId}/images`;

		// Правильное формирование URL с параметрами запроса
		if (limit) {
		  url += `?limit=${limit}`;
		}

		console.log('Fetching user images from URL:', url);

		const response = await fetch(url, {
		  credentials: 'include'
		});

		if (!response.ok) {
		  const errorText = await response.text();
		  console.error('Error response from server:', errorText);
		  throw new Error('Error getting user images');
		}

		return await response.json();
	  } catch (error) {
		console.error('Error fetching user images:', error);
		return [];
	  }
	}),

	    // Get user's posts
  getUserPosts: debugApiCall('/users/:id/posts', async function(userId) {
	try {
	  const response = await fetch(`${API_URL}/users/${userId}/posts`, {
	  credentials: 'include'  // Add this
	});

	  if (!response.ok) {
		throw new Error('Error loading user posts');
	  }

	  return await response.json();
	} catch (error) {
	  console.error('Error fetching user posts:', error);
	  return [];
	}
  }),
};
