import { useEffect } from 'react'
import { useAuthStore } from '@/store/authStore'

export function useAuth() {
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    fetchUser,
    clearError,
  } = useAuthStore()

  useEffect(() => {
    // Fetch user on mount if we have a token
    const token = localStorage.getItem('access_token')
    if (token && !user) {
      fetchUser()
    }
  }, [])

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
    refetchUser: fetchUser,
  }
}
