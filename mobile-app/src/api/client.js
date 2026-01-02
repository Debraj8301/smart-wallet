import axios from 'axios';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { replace } from '../navigation/NavigationService';

// For Android Emulator use 10.0.2.2
// For physical device, use your machine's local IP address (e.g., http://192.168.1.24:8000)
// Current detected IP: 192.168.1.24
const DEV_URL = 'http://192.168.1.24:8000';

const client = axios.create({
  baseURL: DEV_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to attach the token dynamically
client.interceptors.request.use(
  async (config) => {
    try {
      const token = await AsyncStorage.getItem('authToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Error fetching token in interceptor:', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle 401 Unauthorized
client.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    if (error.response && error.response.status === 401) {
      console.log('Session expired or invalid token. Logging out...');
      try {
        await AsyncStorage.removeItem('authToken');
        // Use replace to reset stack and go to Login
        replace('Login');
      } catch (e) {
        console.error('Error clearing token:', e);
      }
    }
    return Promise.reject(error);
  }
);

export const setAuthToken = async (token) => {
  if (token) {
    try {
      await AsyncStorage.setItem('authToken', token);
    } catch (e) {
      console.error('Failed to save token:', e);
    }
  } else {
    try {
      await AsyncStorage.removeItem('authToken');
    } catch (e) {
      console.error('Failed to remove token:', e);
    }
  }
};

export const loadAuthToken = async () => {
    try {
        const token = await AsyncStorage.getItem('authToken');
        return token;
    } catch (e) {
        console.error('Failed to load token:', e);
    }
    return null;
};

export default client;
