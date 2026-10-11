import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'

export function NotFoundPage() {
  const { isAuthenticated } = useAuth()
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <p className="text-sm font-medium text-muted-foreground">404</p>
      <h1 className="text-3xl font-bold">Page not found</h1>
      <p className="max-w-sm text-muted-foreground">
        The page you're looking for doesn't exist or has moved.
      </p>
      <Button asChild className="mt-4">
        <Link to={isAuthenticated ? '/dashboard' : '/'}>{isAuthenticated ? 'Back to dashboard' : 'Go home'}</Link>
      </Button>
    </div>
  )
}
