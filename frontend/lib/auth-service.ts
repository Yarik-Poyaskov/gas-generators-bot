import api from './api';
import { TokenResponse } from '../types';

export const authService = {
  async requestCode(identifier: string): Promise<{ message: string }> {
    const response = await api.post('/auth/request-code', { identifier });
    return response.data;
  },

  async verifyCode(identifier: string, code: string): Promise<TokenResponse> {
    const response = await api.post('/auth/verify-code', { identifier, code });
    const data = response.data;
    
    // Save to localStorage for client-side persistence
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user_role', data.role);
      localStorage.setItem('full_name', data.full_name);
    }
    
    return data;
  },

  async refreshToken(): Promise<TokenResponse | null> {
    try {
      const response = await api.post('/auth/refresh');
      const data = response.data;
      
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user_role', data.role);
        localStorage.setItem('full_name', data.full_name);
      }
      return data;
    } catch (error) {
      console.error('Failed to refresh token:', error);
      return null;
    }
  },

  logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('full_name');
      window.location.href = '/login';
    }
  },

  isAuthenticated(): boolean {
    if (typeof window !== 'undefined') {
      return !!localStorage.getItem('access_token');
    }
    return false;
  },

  getUserRole(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('user_role');
    }
    return null;
  },

  getFullName(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('full_name');
    }
    return null;
  }
};
