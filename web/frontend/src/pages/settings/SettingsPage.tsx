import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Database, ChevronRight, Webhook, Mail, Server, Code, Link2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

export function SettingsPage() {
  const { user, logout } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [currentPassword, setCurrentPassword] = useState('')
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
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <div className="bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Profile</h2>
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
        <h2 className="text-lg font-semibold mb-4">Change Password</h2>
        <form onSubmit={handleUpdateProfile} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              minLength={8}
            />
          </div>
          <Button type="submit" disabled={!newPassword || updateProfileMutation.isPending}>
            Update Password
          </Button>
        </form>
      </div>

      {/* Feature Links */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Features</h2>
        
        {/* Data Sources */}
        <Link to="/settings/data-sources" className="block">
          <div className="bg-card rounded-xl border p-4 hover:border-primary transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <Database className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Custom Data Sources</h3>
                  <p className="text-sm text-muted-foreground">
                    Connect databases, APIs, or upload CSV files
                  </p>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </div>
          </div>
        </Link>

        {/* Data Delivery */}
        <Link to="/settings/delivery" className="block">
          <div className="bg-card rounded-xl border p-4 hover:border-primary transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-lg bg-green-100 flex items-center justify-center">
                  <Webhook className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Data Delivery</h3>
                  <p className="text-sm text-muted-foreground">
                    Webhooks, SFTP, and email subscriptions
                  </p>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </div>
          </div>
        </Link>

        {/* Embeds & Shares */}
        <Link to="/settings/embeds" className="block">
          <div className="bg-card rounded-xl border p-4 hover:border-primary transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-lg bg-purple-100 flex items-center justify-center">
                  <Code className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Embeds & Shares</h3>
                  <p className="text-sm text-muted-foreground">
                    Public share links and embeddable widgets
                  </p>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </div>
          </div>
        </Link>
      </div>

      {/* Subscription */}
      <div className="bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Subscription</h2>
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

      {/* Danger Zone */}
      <div className="bg-card rounded-xl border border-destructive/50 p-6">
        <h2 className="text-lg font-semibold text-destructive mb-4">Danger Zone</h2>
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

