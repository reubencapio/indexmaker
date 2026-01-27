
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Users, Activity, Layers } from 'lucide-react'
import axios from 'axios'
import { useAuth } from '@/hooks/useAuth'

interface AdminStats {
    total_users: number
    active_users: number
    total_indices: number
}

export function AdminDashboardPage() {
    const [stats, setStats] = useState<AdminStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const { user } = useAuth()

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const token = localStorage.getItem('access_token')
                const response = await axios.get('/api/v1/admin/stats', {
                    headers: { Authorization: `Bearer ${token}` },
                })
                setStats(response.data)
            } catch (err: any) {
                console.error('Failed to fetch stats:', err)
                setError('Failed to load dashboard statistics.')
            } finally {
                setLoading(false)
            }
        }

        if (user?.role === 'admin') {
            fetchStats()
        }
    }, [user])

    if (loading) {
        return <div>Loading dashboard...</div>
    }

    if (error) {
        return <div className="text-red-500">{error}</div>
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
                <p className="text-muted-foreground">
                    Platform overview and key metrics.
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Users</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total_users}</div>
                        <p className="text-xs text-muted-foreground">
                            Registered accounts
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Active Users</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.active_users}</div>
                        <p className="text-xs text-muted-foreground">
                            Users with active status
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Indices</CardTitle>
                        <Layers className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total_indices}</div>
                        <p className="text-xs text-muted-foreground">
                            Indices created by users
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
