import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export function AdminRoute({ children }: { children: React.ReactNode }) {
    const { user, isAuthenticated, isLoading } = useAuth()
    const location = useLocation()

    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        )
    }

    // If not logged in, go to login
    if (!isAuthenticated || !user) {
        return <Navigate to="/login" state={{ from: location }} replace />
    }

    // If logged in but not admin, go to dashboard
    // Note: Adjust the role check string if needed ('admin', 'ADMIN', etc.)
    if (user.role?.toLowerCase() !== 'admin') {
        return <Navigate to="/dashboard" replace />
    }

    return <>{children}</>
}
