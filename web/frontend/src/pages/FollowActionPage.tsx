import { useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { BellOff, CheckCircle2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { publicApi } from '@/lib/api'

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <div className="w-full max-w-md rounded-xl border bg-background p-8 text-center shadow-sm">{children}</div>
    </div>
  )
}

/**
 * Landing page for the links in follower emails: `/follow/confirm/:token` and
 * `/follow/unsubscribe/:token`.
 *
 * Confirming happens on arrival, because that is what clicking the link in the
 * email means. Unsubscribing waits for a button press: mail scanners open links
 * in messages, and one of those must not silently remove a subscriber.
 */
export function FollowActionPage({ action }: { action: 'confirm' | 'unsubscribe' }) {
  const { token } = useParams<{ token: string }>()
  const { mutate, ...request } = useMutation({
    mutationFn: () => (action === 'confirm' ? publicApi.confirmFollow(token!) : publicApi.unsubscribeFollow(token!)),
    // The page explains its own failures; no toast on top.
    onError: () => undefined,
  })

  useEffect(() => {
    if (action === 'confirm') mutate()
  }, [action, mutate])

  if (request.isPending || (action === 'confirm' && request.isIdle)) {
    return (
      <Shell>
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
      </Shell>
    )
  }

  if (request.isError) {
    return (
      <Shell>
        <h1 className="text-xl font-semibold">
          {action === 'confirm' ? "This link isn't valid" : "You're not subscribed"}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {action === 'confirm'
            ? 'It may have been used to unsubscribe already. Follow the index again from its page to get a new link.'
            : "This address isn't on the list, so you won't receive any more emails about this index."}
        </p>
        <Button asChild variant="outline" className="mt-6">
          <Link to="/">Go to IndexMaker</Link>
        </Button>
      </Shell>
    )
  }

  if (action === 'unsubscribe' && request.isIdle) {
    return (
      <Shell>
        <BellOff className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
        <h1 className="text-xl font-semibold">Stop following this index?</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          You won't get any more emails about it, and your address will be deleted.
        </p>
        <Button className="mt-6" onClick={() => mutate()}>
          Unsubscribe
        </Button>
      </Shell>
    )
  }

  const share = request.data!
  return (
    <Shell>
      {action === 'confirm' ? (
        <CheckCircle2 className="mx-auto mb-3 h-8 w-8 text-emerald-600" />
      ) : (
        <BellOff className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
      )}
      <h1 className="text-xl font-semibold">
        {action === 'confirm' ? `You're following ${share.title}` : `You've unfollowed ${share.title}`}
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">
        {action === 'confirm'
          ? "We'll email you when it is rebalanced. Every email has an unsubscribe link."
          : "You won't receive any more emails about it."}
      </p>
      <Button asChild variant="outline" className="mt-6">
        <Link to={`/public/${share.slug}`}>View the index</Link>
      </Button>
    </Shell>
  )
}
