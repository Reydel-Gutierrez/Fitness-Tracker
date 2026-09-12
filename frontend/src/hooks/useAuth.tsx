import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, getToken, setToken } from '@/lib/api'
import type { Profile } from '@/types'

type AuthCtx = {
  profile: Profile | null
  loading: boolean
  login: (email: string, password: string) => Promise<Profile>
  register: (name: string, email: string, password: string) => Promise<Profile>
  logout: () => void
  refresh: () => Promise<void>
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)

  async function refresh() {
    if (!getToken()) {
      setProfile(null)
      setLoading(false)
      return
    }
    try {
      const me = await api.get<Profile>('/api/auth/me')
      setProfile(me)
    } catch {
      setToken(null)
      setProfile(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function login(email: string, password: string) {
    const res = await api.post<{ access_token: string; user: Profile }>('/api/auth/login', { email, password })
    setToken(res.access_token)
    setProfile(res.user)
    return res.user
  }

  async function register(name: string, email: string, password: string) {
    const res = await api.post<{ access_token: string; user: Profile }>('/api/auth/register', { name, email, password })
    setToken(res.access_token)
    setProfile(res.user)
    return res.user
  }

  function logout() {
    setToken(null)
    setProfile(null)
  }

  return <Ctx.Provider value={{ profile, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>
}

export function useAuth() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth')
  return ctx
}
