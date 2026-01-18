import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Settings as SettingsIcon, User, Lock, CreditCard, Bell, Shield } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

export function SettingsPage() {
  const { user, logout } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [newPassword, setNewPassword] = useState('')

  const updateProfileMutation = useMutation({
    mutationFn: async (data: { full_name?: string; password?: string }) => {
      const response = await api.patch('/users/me', data)
      return response.data
    },
  })

  const handleUpdateProfile = (e: React.FormEvent) => {
    e.preventDefault()
    const data: { full_name?: string; password?: string } = {}
    if (fullName !== user?.full_name) data.full_name = fullName
    if (newPassword) data.password = newPassword
    if (Object.keys(data).length > 0) {
      updateProfileMutation.mutate(data)
    }
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <SettingsIcon className="h-8 w-8 text-primary" />
          Settings
        </h1>
        <p className="text-muted-foreground mt-2">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <User className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Profile</h2>
        </div>
        <form onSubmit={handleUpdateProfile} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={user?.email}
              disabled
              className="w-full px-3 py-2 border rounded-lg bg-muted text-muted-foreground"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <Button type="submit" disabled={updateProfileMutation.isPending}>
            {updateProfileMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </form>
      </div>

      {/* Password */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <Lock className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Change Password</h2>
        </div>
        <form onSubmit={handleUpdateProfile} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              minLength={8}
              placeholder="Enter new password (min 8 characters)"
            />
          </div>
          <Button type="submit" disabled={!newPassword || updateProfileMutation.isPending}>
            Update Password
          </Button>
        </form>
      </div>

      {/* Subscription */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <CreditCard className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Subscription</h2>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium capitalize">{user?.tier} Plan</p>
            <p className="text-sm text-muted-foreground">
              {user?.tier === 'free' ? '3 indices included' : 
               user?.tier === 'pro' ? '25 indices included' : 'Unlimited indices'}
            </p>
          </div>
          {user?.tier === 'free' && (
            <Button variant="outline">Upgrade to Pro</Button>
          )}
        </div>
      </div>

      {/* Notifications (placeholder) */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <Bell className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Notifications</h2>
        </div>
        <div className="space-y-4">
          <label className="flex items-center justify-between">
            <div>
              <p className="font-medium">Email notifications</p>
              <p className="text-sm text-muted-foreground">Receive updates about your indices</p>
            </div>
            <input type="checkbox" defaultChecked className="h-4 w-4 rounded border-gray-300" />
          </label>
          <label className="flex items-center justify-between">
            <div>
              <p className="font-medium">Rebalancing alerts</p>
              <p className="text-sm text-muted-foreground">Get notified when rebalancing is due</p>
            </div>
            <input type="checkbox" defaultChecked className="h-4 w-4 rounded border-gray-300" />
          </label>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-card rounded-xl border border-destructive/50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="h-5 w-5 text-destructive" />
          <h2 className="text-lg font-semibold text-destructive">Danger Zone</h2>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Sign Out</p>
            <p className="text-sm text-muted-foreground">End your current session</p>
          </div>
          <Button variant="destructive" onClick={logout}>
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  )
}

