// Common types used across the application

export interface User {
  id: number;
  username: string;
  created_at: string;
}

export interface InitRequest {
  username: string;
  password: string;
  email: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
