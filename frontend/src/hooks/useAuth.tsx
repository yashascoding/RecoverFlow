import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import type { AuthUser } from '@/api/auth'

interface AuthContextType {
  user: AuthUser | null
  token: string | null
  loading: boolean
  setAuth: (token: string, user: AuthUser) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

function getStoredToken(): string | null {
  return localStorage.getItem('rf_token')
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(getStoredToken)
  const [loading, setLoading] = useState(() => !!getStoredToken())

  const setAuth = useCallback((newToken: string, newUser: AuthUser) => {
    localStorage.setItem('rf_token', newToken)
    setToken(newToken)
    setUser(newUser)
    setLoading(false)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('rf_token')
    setToken(null)
    setUser(null)
    setLoading(false)
  }, [])

  const value: AuthContextType = {
    user,
    token,
    loading,
    setAuth,
    logout,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
