import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { PlusCircle, Search } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { indicesApi } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'

export function IndicesPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>()

  const { data: indices, isLoading } = useQuery({
    queryKey: ['indices', statusFilter],
    queryFn: () => indicesApi.list({ status: statusFilter }),
  })

  const filteredIndices = indices?.filter((index: any) =>
    index.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    index.identifier.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Indices</h1>
          <p className="text-muted-foreground">Manage your custom financial indices</p>
        </div>
        <Link to="/indices/new">
          <Button>
            <PlusCircle className="h-4 w-4 mr-2" />
            New Index
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search indices..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <select
          value={statusFilter || ''}
          onChange={(e) => setStatusFilter(e.target.value || undefined)}
          className="px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All Status</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {/* Index List */}
      <div className="bg-card rounded-xl border overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Loading...</div>
        ) : filteredIndices?.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            {searchQuery ? (
              <p>No indices found matching "{searchQuery}"</p>
            ) : (
              <div className="space-y-4">
                <p>No indices yet</p>
                <Link to="/indices/new">
                  <Button>
                    <PlusCircle className="h-4 w-4 mr-2" />
                    Create Your First Index
                  </Button>
                </Link>
              </div>
            )}
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                  Name
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                  Identifier
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                  Components
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                  Value
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                  Status
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredIndices?.map((index: any) => (
                <tr key={index.id} className="hover:bg-muted/50 transition-colors">
                  <td className="px-6 py-4">
                    <Link
                      to={`/indices/${index.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {index.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4 font-mono text-sm">{index.identifier}</td>
                  <td className="px-6 py-4">{index.component_count}</td>
                  <td className="px-6 py-4">
                    {index.current_value ? formatCurrency(index.current_value) : '-'}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                        index.status === 'active'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                          : index.status === 'draft'
                          ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
                          : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                      }`}
                    >
                      {index.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {formatDate(index.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

