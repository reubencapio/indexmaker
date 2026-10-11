import { useEffect } from 'react'
import { useAuthStore } from '@/store/authStore'

// The persisted user is a cache. It is refreshed once per page load so a change
// made elsewhere -- an upgrade completed by webhook, a tier set by an admin --
// shows up without the user having to sign out and back in.
let refreshedThisLoad = false

export function useAuth() {
  const {
    user,
    isAuthenticated,
    isLoading,
    sessionChecked,
    error,
    login,
    register,
    logout,
    fetchUser,
    clearError,
  } = useAuthStore()

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token && (!user || !refreshedThisLoad)) {
      refreshedThisLoad = true
      fetchUser()
    }
  }, [])

  return {
    user,
    isAuthenticated,
    // A stored token that has not been checked yet is still "loading": deciding
    // signed-out before the check finishes bounced valid sessions to the login page.
    isLoading: isLoading || (!isAuthenticated && !sessionChecked && !!localStorage.getItem('access_token')),
    error,
    login,
    register,
    logout,
    clearError,
    refetchUser: fetchUser,
  }
}
