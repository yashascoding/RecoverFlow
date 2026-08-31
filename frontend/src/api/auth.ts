import { api } from './client'

export interface AuthUser {
  id: string
  email: string
  name: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export async function register(email: string, password: string, name: string): Promise<AuthResponse> {
  return api.post<AuthResponse>('/api/auth/register', { email, password, name })
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return api.post<AuthResponse>('/api/auth/login', { email, password })
}

export async function getMe(): Promise<AuthUser> {
  return api.get<AuthUser>('/api/auth/me')
}
