import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Clock, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { paymentsApi } from '@/lib/api'

type State = 'verifying' | 'active' | 'pending'

const MAX_ATTEMPTS = 6
const RETRY_MS = 2000

export function PaymentSuccessPage() {
  const [searchParams] = useSearchParams()
  const sessionId = searchParams.get('session_id')
  const { refetchUser } = useAuth()
  const queryClient = useQueryClient()
  const [state, setState] = useState<State>(sessionId ? 'verifying' : 'pending')
  const started = useRef(false)

  useEffect(() => {
    if (!sessionId || started.current) return
    started.current = true
    let cancelled = false

    // Ask the server to confirm the session rather than assuming the webhook
    // has landed. Retried briefly: Stripe can take a moment to finalise.
    const verify = async (attempt: number) => {
      try {
        const summary = await paymentsApi.verifySession(sessionId)
        if (cancelled) return
        if (summary.tier !== 'free') {
          queryClient.setQueryData(['billing', 'subscription'], summary)
          await refetchUser()
          setState('active')
          return
        }
      } catch {
        // Fall through to retry; a final failure shows the "pending" message.
      }
      if (cancelled) return
      if (attempt < MAX_ATTEMPTS) {
        setTimeout(() => verify(attempt + 1), RETRY_MS)
      } else {
        setState('pending')
      }
    }

    verify(1)
    return () => {
      cancelled = true
    }
  }, [sessionId, refetchUser, queryClient])

  if (state === 'verifying') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
        <Loader2 className="mb-6 h-10 w-10 animate-spin text-muted-foreground" />
        <h1 className="mb-2 text-2xl font-bold">Confirming your payment…</h1>
        <p className="text-muted-foreground">This only takes a few seconds.</p>
      </div>
    )
  }

  if (state === 'pending') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
        <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-amber-100">
          <Clock className="h-10 w-10 text-amber-600" />
        </div>
        <h1 className="mb-2 text-3xl font-bold">We're still confirming your payment</h1>
        <p className="mb-8 max-w-md text-muted-foreground">
          Your plan will update automatically as soon as the payment is confirmed, usually within a
          minute. If it hasn't changed after that, contact us and we'll sort it out straight away.
        </p>
        <div className="flex gap-4">
          <Button asChild size="lg">
            <Link to="/settings">View billing</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link to="/contact">Contact support</Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
        <CheckCircle className="h-10 w-10 text-green-600" />
      </div>
      <h1 className="mb-2 text-3xl font-bold">You're on Pro</h1>
      <p className="mb-8 max-w-md text-muted-foreground">
        Thanks for upgrading. Longer analytics history, CSV exports, unlimited sharing and webhooks
        are unlocked on your account now. A receipt is on its way to your inbox.
      </p>
      <div className="flex gap-4">
        <Button asChild size="lg">
          <Link to="/indices">Go to my indices</Link>
        </Button>
        <Button asChild variant="outline" size="lg">
          <Link to="/settings">Manage billing</Link>
        </Button>
      </div>
    </div>
  )
}
