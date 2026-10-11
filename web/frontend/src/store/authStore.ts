import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi, getErrorMessage } from '@/lib/api'

interface User {
  id: string
  email: string
  full_name: string | null
  role: string
  tier: string
  is_active: boolean
  is_verified: boolean
  subscription_status?: string | null
  subscription_interval?: 'month' | 'year' | null
  subscription_current_period_end?: string | null
  subscription_cancel_at_period_end?: boolean
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  // True once the stored token has been checked with the server this page load.
  sessionChecked: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      sessionChecked: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const data = await authApi.login(email, password)
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          await get().fetchUser()
        } catch (error: any) {
          set({
            error: getErrorMessage(error, 'Login failed'),
            isLoading: false,
          })
          throw error
        }
      },

      register: async (email: string, password: string, fullName?: string) => {
        set({ isLoading: true, error: null })
        try {
          await authApi.register(email, password, fullName)
          // Auto-login after registration
          await get().login(email, password)
        } catch (error: any) {
          set({
            error: getErrorMessage(error, 'Registration failed'),
            isLoading: false,
          })
          throw error
        }
      },

      logout: () => {
        authApi.logout()
        set({ user: null, isAuthenticated: false })
      },

      fetchUser: async () => {
        const token = localStorage.getItem('access_token')
        if (!token) {
          set({ isLoading: false, isAuthenticated: false, sessionChecked: true })
          return
        }

        // Only block the UI when there is no user to show yet. A refresh of an
        // already-loaded session happens quietly in the background.
        if (!get().user) set({ isLoading: true })
        try {
          const user = await authApi.me()
          set({ user, isAuthenticated: true, isLoading: false, sessionChecked: true })
        } catch (error: any) {
          const status = error?.response?.status
          if (status === 401 || status === 403 || !localStorage.getItem('access_token')) {
            set({ user: null, isAuthenticated: false, isLoading: false, sessionChecked: true })
            authApi.logout()
          } else {
            // Network blip or server error: the session itself is not known to
            // be bad, so keep whoever was signed in rather than logging them out.
            set({ isLoading: false, sessionChecked: true })
          }
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
