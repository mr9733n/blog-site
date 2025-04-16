// src/config.js

// API configuration
export const API_URL = '/api';

// Authentication settings
export const AUTH_SETTINGS = {
  // Inactivity threshold in milliseconds (5 minutes)
  INACTIVITY_THRESHOLD: 5 * 60 * 1000,

  // Token expiration buffer in seconds (preemptive refresh)
  TOKEN_EXPIRATION_BUFFER: 60,

  // Default token lifetime in seconds (if not provided by server)
  DEFAULT_TOKEN_LIFETIME: 3600
};

// Routes configuration
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  PROFILE: '/profile',
  CREATE_POST: '/create',
  EDIT_POST: '/edit',
  VIEW_POST: '/post'
};

// App configuration
export const APP_CONFIG = {
  APP_NAME: 'My Blog',
  COPYRIGHT_YEAR: 2025,
  COPYRIGHT_TEXT: 'All rights reserved'
};