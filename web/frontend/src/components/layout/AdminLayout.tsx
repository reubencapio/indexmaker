import { useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import {
    LayoutDashboard,
    Users,
    LogOut,
    Menu,
    X,
    ArrowLeft,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'

const navigation = [
    { name: 'Dashboard', href: '/admin/dashboard', icon: LayoutDashboard },
    { name: 'Users', href: '/admin/users', icon: Users },
    //   { name: 'Settings', href: '/admin/settings', icon: Settings },
]

export function AdminLayout() {
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const location = useLocation()
    const { logout, user } = useAuth()

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* Mobile sidebar backdrop */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 z-40 bg-gray-900/50 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <div
                className={cn(
                    'fixed inset-y-0 left-0 z-50 w-64 transform bg-white dark:bg-gray-800 shadow-lg transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-0',
                    sidebarOpen ? 'translate-x-0' : '-translate-x-full'
                )}
            >
                <div className="flex h-full flex-col">
                    {/* Header */}
                    <div className="flex h-16 items-center justify-between px-6 border-b dark:border-gray-700">
                        <span className="text-xl font-bold text-primary">Admin Panel</span>
                        <button
                            className="lg:hidden"
                            onClick={() => setSidebarOpen(false)}
                        >
                            <X className="h-6 w-6" />
                        </button>
                    </div>

                    {/* Nav */}
                    <nav className="flex-1 space-y-1 px-4 py-6">
                        {navigation.map((item) => {
                            const isActive = location.pathname === item.href
                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    className={cn(
                                        'group flex items-center rounded-md px-2 py-2 text-sm font-medium transition-colors',
                                        isActive
                                            ? 'bg-primary text-primary-foreground'
                                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                    )}
                                >
                                    <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                                    {item.name}
                                </Link>
                            )
                        })}
                    </nav>

                    {/* Footer */}
                    <div className="border-t dark:border-gray-700 p-4 space-y-2">
                        <Link to="/dashboard">
                            <Button variant="ghost" className="w-full justify-start text-gray-700 dark:text-gray-300">
                                <ArrowLeft className="mr-3 h-5 w-5" />
                                Back to App
                            </Button>
                        </Link>
                        <div className="flex items-center px-2 py-2">
                            <div className="ml-3">
                                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    {user?.full_name || 'Admin'}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    {user?.email}
                                </p>
                            </div>
                        </div>
                        <Button
                            variant="outline"
                            className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                            onClick={() => logout()}
                        >
                            <LogOut className="mr-3 h-5 w-5" />
                            Sign out
                        </Button>
                    </div>
                </div>
            </div>

            {/* Main content */}
            <div className="flex flex-1 flex-col lg:pl-64 transition-all duration-200">
                <header className="sticky top-0 z-10 flex h-16 items-center gap-x-4 border-b bg-white dark:bg-gray-800 px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
                    <button
                        type="button"
                        className="-m-2.5 p-2.5 text-gray-700 lg:hidden"
                        onClick={() => setSidebarOpen(true)}
                    >
                        <span className="sr-only">Open sidebar</span>
                        <Menu className="h-6 w-6" aria-hidden="true" />
                    </button>

                    <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
                        <div className="flex flex-1" />
                    </div>
                </header>

                <main className="py-10">
                    <div className="px-4 sm:px-6 lg:px-8">
                        <Outlet />
                    </div>
                </main>
            </div>
        </div>
    )
}
