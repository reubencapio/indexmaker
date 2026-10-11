import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Settings as SettingsIcon, User, Lock, CreditCard, LogOut, AlertTriangle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { useAuth } from '@/hooks/useAuth'
import { useBillingActions, useSubscription } from '@/hooks/useBilling'
import { Button } from '@/components/ui/button'
import { api, getErrorMessage, type SubscriptionSummary } from '@/lib/api'
import { formatDate } from '@/lib/utils'

const inputClass =
  'w-full px-3 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary'

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const ratio = limit ? Math.min(used / limit, 1) : 0
  const full = limit !== null && used >= limit
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>{label}</span>
        <span className={full ? 'font-medium text-amber-600' : 'text-muted-foreground'}>
          {used} / {limit ?? 'Unlimited'}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${full ? 'bg-amber-500' : 'bg-blue-600'}`}
          style={{ width: `${limit ? ratio * 100 : 0}%` }}
        />
      </div>
    </div>
  )
}

function subscriptionLine(sub: SubscriptionSummary): string {
  if (sub.tier === 'free') return 'You are on the Free plan.'
  if (!sub.status) return `${sub.plan.name} plan, managed by our team.`
  const end = sub.current_period_end ? formatDate(sub.current_period_end) : null
  const cadence = sub.interval === 'year' ? 'annually' : 'monthly'
  if (sub.cancel_at_period_end) {
    return end ? `Cancelled. You keep ${sub.plan.name} until ${end}.` : `Cancelled. ${sub.plan.name} ends with this period.`
  }
  if (sub.status === 'trialing') {
    return end ? `Free trial. Your first payment is on ${end}.` : 'Free trial in progress.'
  }
  if (sub.status === 'past_due') return 'Your last payment failed. Update your card to keep Pro.'
  return end ? `Billed ${cadence}. Renews on ${end}.` : `Billed ${cadence}.`
}

export function SettingsPage() {
  const { user, logout, refetchUser } = useAuth()
  const subscription = useSubscription()
  const { openPortal, pending } = useBillingActions()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const profileMutation = useMutation({
    mutationFn: async (full_name: string) => (await api.patch('/users/me', { full_name })).data,
    onSuccess: async () => {
      await refetchUser()
      toast.success('Profile updated')
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Could not update your profile.')),
  })

  const passwordMutation = useMutation({
    mutationFn: async () =>
      (await api.patch('/users/me', { password: newPassword, current_password: currentPassword })).data,
    onSuccess: () => {
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      toast.success('Password changed')
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Could not change your password.')),
  })

  const passwordsMatch = newPassword === confirmPassword
  const canChangePassword = currentPassword.length > 0 && newPassword.length >= 8 && passwordsMatch
  const sub = subscription.data

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <SettingsIcon className="h-8 w-8 text-primary" />
          Settings
        </h1>
        <p className="text-muted-foreground mt-2">Manage your account, plan and billing</p>
      </div>

      {/* Plan & billing */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <CreditCard className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Plan &amp; billing</h2>
        </div>

        {subscription.isLoading && <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />}
        {subscription.isError && (
          <p className="text-sm text-muted-foreground">
            Couldn't load your plan.{' '}
            <button className="underline" onClick={() => subscription.refetch()}>
              Retry
            </button>
          </p>
        )}

        {sub && (
          <div className="space-y-6">
            {sub.status === 'past_due' && (
              <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p>
                  We couldn't take your last payment. Update your payment method to avoid losing Pro
                  features.
                </p>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="font-medium">{sub.plan.name} plan</p>
                <p className="text-sm text-muted-foreground">{subscriptionLine(sub)}</p>
              </div>
              <div className="flex gap-2">
                {sub.has_billing_account && (
                  <Button variant="outline" onClick={openPortal} disabled={pending !== null}>
                    {pending === 'portal' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {sub.status === 'past_due' ? 'Update payment method' : 'Manage billing'}
                  </Button>
                )}
                {sub.tier === 'free' && (
                  <Button asChild className="bg-blue-600 hover:bg-blue-700">
                    <Link to="/pricing">Upgrade</Link>
                  </Button>
                )}
              </div>
            </div>
            {sub.has_billing_account && (
              <p className="-mt-3 text-xs text-muted-foreground">
                Change plan, update your card, download invoices or cancel, all on Stripe's secure
                billing page.
              </p>
            )}

            <div className="space-y-4 border-t pt-4">
              <p className="text-sm font-medium">Usage</p>
              <UsageBar label="Indices" used={sub.usage.indices} limit={sub.plan.max_indices} />
              <UsageBar label="Custom data sources" used={sub.usage.data_sources} limit={sub.plan.max_data_sources} />
              <UsageBar label="Public share links" used={sub.usage.public_shares} limit={sub.plan.max_public_shares} />
              <UsageBar label="Embed widgets" used={sub.usage.embed_widgets} limit={sub.plan.max_embed_widgets} />
            </div>
          </div>
        )}
      </div>

      {/* Profile */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <User className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Profile</h2>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            profileMutation.mutate(fullName.trim())
          }}
          className="space-y-4"
        >
          <div>
            <label htmlFor="settings-email" className="block text-sm font-medium mb-1">Email</label>
            <input
              id="settings-email"
              type="email"
              value={user?.email ?? ''}
              disabled
              className="w-full px-3 py-2 border rounded-lg bg-muted text-muted-foreground"
            />
          </div>
          <div>
            <label htmlFor="settings-name" className="block text-sm font-medium mb-1">Full name</label>
            <input
              id="settings-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className={inputClass}
              autoComplete="name"
            />
          </div>
          <Button
            type="submit"
            disabled={profileMutation.isPending || fullName.trim() === (user?.full_name || '')}
          >
            {profileMutation.isPending ? 'Saving...' : 'Save changes'}
          </Button>
        </form>
      </div>

      {/* Password */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <Lock className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Change password</h2>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (canChangePassword) passwordMutation.mutate()
          }}
          className="space-y-4"
        >
          <div>
            <label htmlFor="current-password" className="block text-sm font-medium mb-1">Current password</label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className={inputClass}
              autoComplete="current-password"
            />
          </div>
          <div>
            <label htmlFor="new-password" className="block text-sm font-medium mb-1">New password</label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className={inputClass}
              minLength={8}
              autoComplete="new-password"
              placeholder="At least 8 characters"
            />
          </div>
          <div>
            <label htmlFor="confirm-password" className="block text-sm font-medium mb-1">Confirm new password</label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={inputClass}
              autoComplete="new-password"
            />
            {confirmPassword && !passwordsMatch && (
              <p className="mt-1 text-sm text-destructive">Passwords don't match.</p>
            )}
          </div>
          <Button type="submit" disabled={!canChangePassword || passwordMutation.isPending}>
            {passwordMutation.isPending ? 'Updating...' : 'Update password'}
          </Button>
        </form>
      </div>

      {/* Session */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Sign out</p>
            <p className="text-sm text-muted-foreground">End your session on this device</p>
          </div>
          <Button variant="outline" onClick={logout}>
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </div>
    </div>
  )
}
