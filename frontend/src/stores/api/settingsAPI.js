import { API_URL } from '../../config';
import { authFetch } from '../authService';
import { debugApiCall } from './apiUtils';


export const settingsAPI = {
    // Token settings
	updateTokenSettings: debugApiCall('/settings/token-settings', async function(tokenLifetime, refreshTokenLifetime) {
	  try {
		console.log('Updating token settings:', { tokenLifetime, refreshTokenLifetime });

		const response = await authFetch(`${API_URL}/settings/token-settings`, {
		  method: 'PUT',
		  headers: {
			'Content-Type': 'application/json'
		  },
		  credentials: 'include',
		  body: JSON.stringify({
			token_lifetime: tokenLifetime,
			refresh_token_lifetime: refreshTokenLifetime
		  })
		});

		if (!response.ok) {
		  console.error('Failed to update token settings, status:', response.status);
		  const error = await response.json();
		  throw new Error(error.msg || 'Error updating settings');
		}

		const data = await response.json();
		console.log('Token settings updated successfully:', data);
		return data;
	  } catch (error) {
		console.error('Error updating token settings:', error);
		throw error;
	  }
	}),

};