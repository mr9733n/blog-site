import { API_URL } from '../../config';
import { authFetch } from '../authService';
import { debugApiCall } from './apiUtils';


export const adminAPI = {
  // Admin functions
  // Get all users (admin only)
  getAllUsers: debugApiCall('/admin/users', async function() {
    try {
      const response = await authFetch(`${API_URL}/admin/users`, {
      credentials: 'include'  // Add this
    });

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
      const response = await authFetch(`${API_URL}/admin/users/${userId}`, {
      credentials: 'include'  // Add this
    });

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

    // Admin functions
  toggleUserBlock: debugApiCall('/admin/users/:userId/block', async function(userId, blockStatus) {
    try {
      const response = await authFetch(`${API_URL}/admin/users/${userId}/block`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
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
        credentials: 'include',
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