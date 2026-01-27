
import { useEffect, useState } from 'react'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { MoreHorizontal, Shield, ShieldOff, Ban, CheckCircle } from 'lucide-react'
import { format } from 'date-fns'
import axios from 'axios'
import { toast } from 'sonner'
import { useAuth } from '@/hooks/useAuth'

interface User {
    id: string
    email: string
    full_name: string
    role: string
    is_active: boolean
    is_verified: boolean
    created_at: string
}

export function UsersPage() {
    const [users, setUsers] = useState<User[]>([])
    const [loading, setLoading] = useState(true)
    const { user: currentUser } = useAuth()

    const fetchUsers = async () => {
        try {
            const token = localStorage.getItem('access_token')
            const response = await axios.get('/api/v1/users', {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (Array.isArray(response.data)) {
                setUsers(response.data)
            } else {
                console.error('Invalid users data received:', response.data)
                setUsers([])
                toast.error('Received invalid user data format')
            }
        } catch (err) {
            console.error('Error fetching users:', err)
            toast.error('Failed to load users')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchUsers()
    }, [])

    const safeFormatDate = (dateString: string) => {
        if (!dateString) return 'N/A'
        try {
            return format(new Date(dateString), 'MMM d, yyyy')
        } catch (e) {
            console.error('Invalid date:', dateString)
            return 'Invalid Date'
        }
    }

    const handleUpdateRole = async (userId: string, newRole: string) => {
        try {
            const token = localStorage.getItem('access_token')
            await axios.patch(
                `/api/v1/users/${userId}`,
                { role: newRole },
                { headers: { Authorization: `Bearer ${token}` } }
            )
            toast.success(`User role updated to ${newRole}`)
            fetchUsers() // Refresh list
        } catch (err) {
            toast.error('Failed to update role')
        }
    }

    const handleToggleActive = async (user: User) => {
        try {
            const token = localStorage.getItem('access_token')
            await axios.patch(
                `/api/v1/users/${user.id}`,
                { is_active: !user.is_active },
                { headers: { Authorization: `Bearer ${token}` } }
            )
            toast.success(`User ${user.is_active ? 'deactivated' : 'activated'}`)
            fetchUsers()
        } catch (err: any) {
            // Show specific error from backend if available (e.g. self-deactivation)
            const msg = err.response?.data?.detail || 'Failed to update status'
            toast.error(msg)
        }
    }

    if (loading) return <div>Loading users...</div>

    // Safety check for render
    if (!Array.isArray(users)) {
        console.error('Users state is not an array:', users)
        return <div>Error: Invalid users data</div>
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Users</h1>
                    <p className="text-muted-foreground">
                        Manage user accounts and permissions.
                    </p>
                </div>
            </div>

            <div className="rounded-md border bg-white dark:bg-gray-800">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>User</TableHead>
                            <TableHead>Role</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Joined</TableHead>
                            <TableHead className="w-[70px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {users.map((u) => (
                            <TableRow key={u.id}>
                                <TableCell>
                                    <div className="flex flex-col">
                                        <span className="font-medium">{u.full_name || 'No Name'}</span>
                                        <span className="text-xs text-muted-foreground">{u.email}</span>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <Badge variant={u.role === 'admin' ? 'default' : 'secondary'}>
                                        {u.role}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <div className="flex items-center gap-2">
                                        {u.is_active ? (
                                            <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50">Active</Badge>
                                        ) : (
                                            <Badge variant="destructive">Inactive</Badge>
                                        )}
                                        {u.is_verified && <CheckCircle className="h-4 w-4 text-blue-500" />}
                                    </div>
                                </TableCell>
                                <TableCell>{safeFormatDate(u.created_at)}</TableCell>
                                <TableCell>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" className="h-8 w-8 p-0">
                                                <span className="sr-only">Open menu</span>
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                            {u.role !== 'admin' ? (
                                                <DropdownMenuItem onClick={() => handleUpdateRole(u.id, 'admin')}>
                                                    <Shield className="mr-2 h-4 w-4" /> Make Admin
                                                </DropdownMenuItem>
                                            ) : (
                                                <DropdownMenuItem onClick={() => handleUpdateRole(u.id, 'user')} disabled={u.id === currentUser?.id}>
                                                    <ShieldOff className="mr-2 h-4 w-4" /> Revoke Admin
                                                </DropdownMenuItem>
                                            )}

                                            {u.is_active ? (
                                                <DropdownMenuItem
                                                    onClick={() => handleToggleActive(u)}
                                                    className="text-red-600"
                                                    disabled={u.id === currentUser?.id}
                                                >
                                                    <Ban className="mr-2 h-4 w-4" /> Deactivate User
                                                </DropdownMenuItem>
                                            ) : (
                                                <DropdownMenuItem onClick={() => handleToggleActive(u)}>
                                                    <CheckCircle className="mr-2 h-4 w-4" /> Activate User
                                                </DropdownMenuItem>
                                            )}
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    )
}
