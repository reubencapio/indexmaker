import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { LineChart } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error, clearError } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { toast } = useToast()

  const redirectUrl = searchParams.get('redirect') || '/dashboard'
  const sessionExpired = searchParams.get('session_expired') === 'true'

  // Show toast if session expired
  useEffect(() => {
    if (sessionExpired) {
      toast({
        title: 'Session Expired',
        description: 'Please log in again to continue.',
        variant: 'default',
      })
    }
  }, [sessionExpired, toast])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await login(email, password)
      // Navigate to the redirect URL or dashboard
      navigate(decodeURIComponent(redirectUrl))
    } catch (err) {
      // Error is handled in the store
    }
  }

  return (
    <div className="space-y-6">
      <div className="lg:hidden flex items-center justify-center gap-2 mb-8">
        <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
          <LineChart className="h-6 w-6 text-primary-foreground" />
        </div>
        <span className="font-bold text-2xl">IndexMaker</span>
      </div>

      <div className="text-center lg:text-left">
        <h1 className="text-2xl font-bold">Welcome back</h1>
        <p className="text-muted-foreground">
          {sessionExpired
            ? 'Your session has expired. Please sign in again.'
            : 'Enter your credentials to access your account'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-lg">
            {error}
            <button onClick={clearError} className="ml-2 underline">
              Dismiss
            </button>
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="you@example.com"
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="password" className="text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="••••••••"
            required
          />
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? 'Signing in...' : 'Sign In'}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Don't have an account?{' '}
        <Link to="/register" className="text-primary hover:underline font-medium">
          Sign up
        </Link>
      </p>
    </div>
  )
}
