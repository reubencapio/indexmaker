import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  LineChart,
  History,
  Settings,
  LogOut,
  PlusCircle,
  Menu,
  X,
  FileText,
  Send,
  Code,
  Database,
  Users,
  LifeBuoy,
  ShieldCheck,
  Sparkles,
  AlertTriangle,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { UpgradeDialog } from '@/components/billing/UpgradeDialog'
import { useSubscription } from '@/hooks/useBilling'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Indices', href: '/indices', icon: LineChart },
  { name: 'Backtests', href: '/backtests', icon: History },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Teams', href: '/teams', icon: Users },
  { name: 'Data Sources', href: '/data-sources', icon: Database },
  { name: 'Data Delivery', href: '/delivery', icon: Send },
  { name: 'Embeds & Shares', href: '/embeds', icon: Code },
  { name: 'Support', href: '/contact', icon: LifeBuoy },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function MainLayout() {
  const location = useLocation()
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { data: subscription } = useSubscription()

  // Close the mobile drawer after navigating; it used to stay open over the
  // page that had just been chosen from it.
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  const indexLimit = subscription?.plan.max_indices ?? null
  const indexUsage = subscription?.usage.indices ?? 0

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-card border-r transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-16 items-center justify-between px-6 border-b">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <LineChart className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-xl">IndexMaker</span>
          </Link>
          <button className="lg:hidden" aria-label="Close menu" onClick={() => setSidebarOpen(false)}>
            <X className="h-6 w-6" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-2">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href || location.pathname.startsWith(`${item.href}/`)
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            )
          })}

          {/* Admin Panel Link - Only visible to admins */}
          {user?.role?.toLowerCase() === 'admin' && (
            <Link
              to="/admin/dashboard"
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors mt-4 border-t pt-4',
                location.pathname.startsWith('/admin')
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <ShieldCheck className="h-5 w-5" />
              Admin Panel
            </Link>
          )}
        </nav>

        {/* Plan usage and upgrade prompt for free users */}
        {subscription?.tier === 'free' && indexLimit !== null && (
          <div className="mx-4 mb-4 rounded-xl border bg-muted/40 p-4">
            <div className="mb-1 flex justify-between text-xs">
              <span className="font-medium">Free plan</span>
              <span className="text-muted-foreground">
                {indexUsage} of {indexLimit} indices
              </span>
            </div>
            <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className={cn('h-full rounded-full', indexUsage >= indexLimit ? 'bg-amber-500' : 'bg-blue-600')}
                style={{ width: `${Math.min(indexUsage / indexLimit, 1) * 100}%` }}
              />
            </div>
            <Link
              to="/pricing"
              className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              <Sparkles className="h-4 w-4" />
              Upgrade to Pro
            </Link>
          </div>
        )}

        <div className="p-4 border-t">
          <Link to="/indices/new">
            <Button className="w-full" size="sm">
              <PlusCircle className="h-4 w-4 mr-2" />
              New Index
            </Button>
          </Link>
        </div>

        <div className="p-4 border-t">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-medium">
                {user?.full_name?.[0] || user?.email?.[0]?.toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {user?.full_name || user?.email}
              </p>
              <p className="text-xs text-muted-foreground capitalize">{user?.tier} Plan</p>
            </div>
            <button
              onClick={logout}
              aria-label="Sign out"
              title="Sign out"
              className="text-muted-foreground hover:text-foreground"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-background/95 backdrop-blur border-b flex items-center px-6">
          <button
            className="lg:hidden mr-4"
            aria-label="Open menu"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex-1" />
        </header>

        {subscription?.status === 'past_due' && (
          <div className="flex flex-wrap items-center gap-2 border-b border-amber-200 bg-amber-50 px-6 py-3 text-sm text-amber-900">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>Your last payment failed.</span>
            <Link to="/settings" className="font-medium underline">
              Update your payment method
            </Link>
            <span>to keep your Pro features.</span>
          </div>
        )}

        {/* Page content */}
        <main className="p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
      <UpgradeDialog />
    </div>
  )
}
