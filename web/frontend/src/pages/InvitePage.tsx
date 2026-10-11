import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Users } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { api, getErrorMessage } from '@/lib/api'

interface Invitation {
  organization_name: string
  email: string
  role: string
  status: 'pending' | 'accepted' | 'declined' | 'expired'
  expires_at: string
}

/** Landing page for a team invitation link. Viewable signed out; accepting needs an account. */
export function InvitePage() {
  const { token } = useParams<{ token: string }>()
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const here = encodeURIComponent(`/invite/${token}`)

  const invitation = useQuery({
    queryKey: ['invitation', token],
    queryFn: async (): Promise<Invitation> =>
      (await api.get(`/organizations/invitations/by-token/${encodeURIComponent(token!)}`)).data,
    retry: false,
  })

  const accept = useMutation({
    mutationFn: async () =>
      (await api.post(`/organizations/invitations/by-token/${encodeURIComponent(token!)}/accept`)).data,
    onSuccess: (data: { organization_name: string }) => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      toast.success(`You've joined ${data.organization_name}`)
      navigate('/teams')
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Could not accept the invitation.')),
  })

  const shell = (children: React.ReactNode) => (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <div className="w-full max-w-md rounded-xl border bg-background p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Users className="h-6 w-6 text-primary" />
        </div>
        {children}
      </div>
    </div>
  )

  if (invitation.isLoading || authLoading) {
    return shell(<Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />)
  }

  if (invitation.isError || !invitation.data) {
    return shell(
      <>
        <h1 className="text-xl font-semibold">This invitation link isn't valid</h1>
        <p className="mt-2 text-sm text-muted-foreground">Ask whoever invited you to send a new one.</p>
        <Button asChild variant="outline" className="mt-6">
          <Link to="/">Go to IndexMaker</Link>
        </Button>
      </>
    )
  }

  const data = invitation.data

  if (data.status !== 'pending') {
    return shell(
      <>
        <h1 className="text-xl font-semibold">
          {data.status === 'expired' ? 'This invitation has expired' : 'This invitation has already been used'}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {data.status === 'expired'
            ? `Ask an admin of ${data.organization_name} to invite you again.`
            : `If you accepted it, ${data.organization_name} is in your teams.`}
        </p>
        <Button asChild className="mt-6">
          <Link to={isAuthenticated ? '/teams' : '/login'}>{isAuthenticated ? 'Go to teams' : 'Sign in'}</Link>
        </Button>
      </>
    )
  }

  const wrongAccount = isAuthenticated && user?.email.toLowerCase() !== data.email.toLowerCase()

  return shell(
    <>
      <h1 className="text-xl font-semibold">Join {data.organization_name}</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        You've been invited to join as <span className="font-medium text-foreground">{data.role}</span>. The
        invitation was sent to <span className="font-medium text-foreground">{data.email}</span>.
      </p>

      {!isAuthenticated && (
        <div className="mt-6 space-y-3">
          <Button asChild className="w-full">
            <Link to={`/login?redirect=${here}`}>Sign in to accept</Link>
          </Button>
          <p className="text-sm text-muted-foreground">
            New here?{' '}
            <Link to={`/register?redirect=${here}`} className="font-medium text-foreground underline">
              Create an account
            </Link>{' '}
            with {data.email}.
          </p>
        </div>
      )}

      {isAuthenticated && !wrongAccount && (
        <Button className="mt-6 w-full" onClick={() => accept.mutate()} disabled={accept.isPending}>
          {accept.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Accept invitation
        </Button>
      )}

      {wrongAccount && (
        <div className="mt-6 space-y-3">
          <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            You're signed in as {user?.email}. Sign in with {data.email} to accept.
          </p>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => {
              logout()
              navigate(`/login?redirect=${here}`)
            }}
          >
            Switch account
          </Button>
        </div>
      )}
    </>
  )
}
