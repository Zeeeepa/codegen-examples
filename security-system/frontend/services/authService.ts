/**
 * Authentication service for handling all authentication-related API calls.
 * Supports local auth, OAuth2, SAML, MFA, and session management.
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';

export interface User {
  id: string;
  email: string;
  username?: string;
  firstName?: string;
  lastName?: string;
  displayName?: string;
  avatarUrl?: string;
  roles: string[];
  permissions: string[];
  mfaEnabled: boolean;
  isVerified: boolean;
  lastLogin?: string;
}

export interface LoginResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  mfaRequired?: boolean;
  mfaToken?: string;
}

export interface MFASetupResponse {
  secret: string;
  qrCodeUrl: string;
  backupCodes: string[];
}

export interface APIKey {
  id: string;
  name: string;
  keyPrefix: string;
  scopes: string[];
  lastUsed?: string;
  expiresAt?: string;
  createdAt: string;
}

export interface Session {
  id: string;
  deviceInfo: string;
  ipAddress: string;
  lastActivity: string;
  isActive: boolean;
  isCurrent: boolean;
}

class AuthService {
  private api: AxiosInstance;
  private baseURL: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private user: User | null = null;

  constructor(baseURL: string = '/api') {
    this.baseURL = baseURL;
    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Load tokens from localStorage
    this.loadTokensFromStorage();

    // Setup request interceptor to add auth header
    this.api.interceptors.request.use(
      (config) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Setup response interceptor for token refresh
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.refreshAccessToken();
            originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
            return this.api(originalRequest);
          } catch (refreshError) {
            this.logout();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private loadTokensFromStorage(): void {
    this.accessToken = localStorage.getItem('accessToken');
    this.refreshToken = localStorage.getItem('refreshToken');
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        this.user = JSON.parse(userStr);
      } catch (e) {
        console.error('Failed to parse user from localStorage:', e);
      }
    }
  }

  private saveTokensToStorage(accessToken: string, refreshToken: string, user: User): void {
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('refreshToken', refreshToken);
    localStorage.setItem('user', JSON.stringify(user));
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.user = user;
  }

  private clearTokensFromStorage(): void {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    this.accessToken = null;
    this.refreshToken = null;
    this.user = null;
  }

  /**
   * Login with email and password
   */
  async login(email: string, password: string, rememberMe: boolean = false): Promise<LoginResponse> {
    try {
      const response: AxiosResponse<LoginResponse> = await this.api.post('/auth/login', {
        email,
        password,
        rememberMe,
      });

      const { user, accessToken, refreshToken, mfaRequired } = response.data;

      if (!mfaRequired) {
        this.saveTokensToStorage(accessToken, refreshToken, user);
      }

      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Login failed');
    }
  }

  /**
   * Verify MFA code
   */
  async verifyMFA(mfaToken: string, code: string): Promise<LoginResponse> {
    try {
      const response: AxiosResponse<LoginResponse> = await this.api.post('/auth/mfa/verify', {
        mfaToken,
        code,
      });

      const { user, accessToken, refreshToken } = response.data;
      this.saveTokensToStorage(accessToken, refreshToken, user);

      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'MFA verification failed');
    }
  }

  /**
   * Register new user
   */
  async register(userData: {
    email: string;
    password: string;
    firstName?: string;
    lastName?: string;
    username?: string;
  }): Promise<{ message: string; user: User }> {
    try {
      const response = await this.api.post('/auth/register', userData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Registration failed');
    }
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      if (this.refreshToken) {
        await this.api.post('/auth/logout', { refreshToken: this.refreshToken });
      }
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      this.clearTokensFromStorage();
    }
  }

  /**
   * Refresh access token
   */
  async refreshAccessToken(): Promise<string> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response: AxiosResponse<{ accessToken: string; refreshToken: string }> = 
        await this.api.post('/auth/refresh', {
          refreshToken: this.refreshToken,
        });

      const { accessToken, refreshToken } = response.data;
      
      if (this.user) {
        this.saveTokensToStorage(accessToken, refreshToken, this.user);
      }

      return accessToken;
    } catch (error: any) {
      this.clearTokensFromStorage();
      throw new Error(error.response?.data?.message || 'Token refresh failed');
    }
  }

  /**
   * Get OAuth2 authorization URL
   */
  async getOAuth2AuthUrl(provider: string, redirectUrl?: string): Promise<string> {
    try {
      const response = await this.api.get(`/auth/oauth2/${provider}/url`, {
        params: { redirectUrl },
      });
      return response.data.authUrl;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Failed to get OAuth2 URL');
    }
  }

  /**
   * Handle OAuth2 callback
   */
  async handleOAuth2Callback(provider: string, code: string, state: string): Promise<LoginResponse> {
    try {
      const response: AxiosResponse<LoginResponse> = await this.api.post(`/auth/oauth2/${provider}/callback`, {
        code,
        state,
      });

      const { user, accessToken, refreshToken } = response.data;
      this.saveTokensToStorage(accessToken, refreshToken, user);

      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'OAuth2 callback failed');
    }
  }

  /**
   * Get SAML authorization URL
   */
  async getSAMLAuthUrl(provider: string, redirectUrl?: string): Promise<string> {
    try {
      const response = await this.api.get(`/auth/saml/${provider}/url`, {
        params: { redirectUrl },
      });
      return response.data.authUrl;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Failed to get SAML URL');
    }
  }

  /**
   * Handle SAML callback
   */
  async handleSAMLCallback(provider: string, samlResponse: string, relayState?: string): Promise<LoginResponse> {
    try {
      const response: AxiosResponse<LoginResponse> = await this.api.post(`/auth/saml/${provider}/callback`, {
        samlResponse,
        relayState,
      });

      const { user, accessToken, refreshToken } = response.data;
      this.saveTokensToStorage(accessToken, refreshToken, user);

      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'SAML callback failed');
    }
  }

  /**
   * Setup MFA for current user
   */
  async setupMFA(): Promise<MFASetupResponse> {
    try {
      const response: AxiosResponse<MFASetupResponse> = await this.api.post('/auth/mfa/setup');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'MFA setup failed');
    }
  }

  /**
   * Enable MFA after setup
   */
  async enableMFA(code: string): Promise<{ message: string; backupCodes: string[] }> {
    try {
      const response = await this.api.post('/auth/mfa/enable', { code });
      
      // Update user MFA status
      if (this.user) {
        this.user.mfaEnabled = true;
        localStorage.setItem('user', JSON.stringify(this.user));
      }

      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'MFA enable failed');
    }
  }

  /**
   * Disable MFA
   */
  async disableMFA(password: string): Promise<{ message: string }> {
    try {
      const response = await this.api.post('/auth/mfa/disable', { password });
      
      // Update user MFA status
      if (this.user) {
        this.user.mfaEnabled = false;
        localStorage.setItem('user', JSON.stringify(this.user));
      }

      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'MFA disable failed');
    }
  }

  /**
   * Change password
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    try {
      const response = await this.api.post('/auth/change-password', {
        currentPassword,
        newPassword,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Password change failed');
    }
  }

  /**
   * Forgot password
   */
  async forgotPassword(email: string): Promise<{ message: string }> {
    try {
      const response = await this.api.post('/auth/forgot-password', { email });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Forgot password request failed');
    }
  }

  /**
   * Reset password
   */
  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    try {
      const response = await this.api.post('/auth/reset-password', {
        token,
        newPassword,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Password reset failed');
    }
  }

  /**
   * Get current user profile
   */
  async getProfile(): Promise<User> {
    try {
      const response: AxiosResponse<User> = await this.api.get('/auth/profile');
      this.user = response.data;
      localStorage.setItem('user', JSON.stringify(this.user));
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Failed to get profile');
    }
  }

  /**
   * Update user profile
   */
  async updateProfile(profileData: Partial<User>): Promise<User> {
    try {
      const response: AxiosResponse<User> = await this.api.put('/auth/profile', profileData);
      this.user = response.data;
      localStorage.setItem('user', JSON.stringify(this.user));
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Profile update failed');
    }
  }

  /**
   * Get user sessions
   */
  async getSessions(): Promise<Session[]> {
    try {
      const response: AxiosResponse<Session[]> = await this.api.get('/auth/sessions');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Failed to get sessions');
    }
  }

  /**
   * Revoke session
   */
  async revokeSession(sessionId: string): Promise<{ message: string }> {
    try {
      const response = await this.api.delete(`/auth/sessions/${sessionId}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Session revocation failed');
    }
  }

  /**
   * Create API key
   */
  async createAPIKey(name: string, scopes: string[], expiresAt?: string): Promise<{ apiKey: string; keyData: APIKey }> {
    try {
      const response = await this.api.post('/auth/api-keys', {
        name,
        scopes,
        expiresAt,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'API key creation failed');
    }
  }

  /**
   * Get API keys
   */
  async getAPIKeys(): Promise<APIKey[]> {
    try {
      const response: AxiosResponse<APIKey[]> = await this.api.get('/auth/api-keys');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Failed to get API keys');
    }
  }

  /**
   * Delete API key
   */
  async deleteAPIKey(keyId: string): Promise<{ message: string }> {
    try {
      const response = await this.api.delete(`/auth/api-keys/${keyId}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'API key deletion failed');
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!(this.accessToken && this.user);
  }

  /**
   * Get current user
   */
  getCurrentUser(): User | null {
    return this.user;
  }

  /**
   * Check if user has permission
   */
  hasPermission(permission: string): boolean {
    if (!this.user) return false;
    return this.user.permissions.includes(permission) || this.user.permissions.includes('*:*');
  }

  /**
   * Check if user has role
   */
  hasRole(role: string): boolean {
    if (!this.user) return false;
    return this.user.roles.includes(role);
  }

  /**
   * Check if user is admin
   */
  isAdmin(): boolean {
    return this.hasRole('admin') || this.hasRole('super_admin');
  }

  /**
   * Get access token
   */
  getAccessToken(): string | null {
    return this.accessToken;
  }

  /**
   * Verify email
   */
  async verifyEmail(token: string): Promise<{ message: string }> {
    try {
      const response = await this.api.post('/auth/verify-email', { token });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Email verification failed');
    }
  }

  /**
   * Resend verification email
   */
  async resendVerificationEmail(): Promise<{ message: string }> {
    try {
      const response = await this.api.post('/auth/resend-verification');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Failed to resend verification email');
    }
  }
}

// Create and export singleton instance
export const authService = new AuthService();
export default authService;

