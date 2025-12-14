import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { LineChart, TrendingUp, BarChart3, PlusCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { indicesApi, backtestsApi } from '@/lib/api'
import { formatCurrency, formatPercent, formatDate } from '@/lib/utils'

export function DashboardPage() {
  const { data: indices, isLoading: indicesLoading } = useQuery({
    queryKey: ['indices'],
    queryFn: () => indicesApi.list({ limit: 5 }),
  })

  const { data: backtests, isLoading: backtestsLoading } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestsApi.list(),
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Overview of your indices and backtests</p>
        </div>
        <Link to="/indices/new">
          <Button>
            <PlusCircle className="h-4 w-4 mr-2" />
            New Index
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="bg-card rounded-xl border p-6">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <LineChart className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Indices</p>
              <p className="text-2xl font-bold">{indices?.length || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-card rounded-xl border p-6">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-lg bg-green-500/10 flex items-center justify-center">
              <TrendingUp className="h-6 w-6 text-green-500" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Active Indices</p>
              <p className="text-2xl font-bold">
                {indices?.filter((i: any) => i.status === 'active').length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-card rounded-xl border p-6">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <BarChart3 className="h-6 w-6 text-blue-500" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Backtests Run</p>
              <p className="text-2xl font-bold">{backtests?.length || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Indices */}
      <div className="bg-card rounded-xl border">
        <div className="p-6 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Indices</h2>
          <Link to="/indices" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </div>
        <div className="divide-y">
          {indicesLoading ? (
            <div className="p-6 text-center text-muted-foreground">Loading...</div>
          ) : indices?.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground">
              No indices yet.{' '}
              <Link to="/indices/new" className="text-primary hover:underline">
                Create your first index
              </Link>
            </div>
          ) : (
            indices?.slice(0, 5).map((index: any) => (
              <Link
                key={index.id}
                to={`/indices/${index.id}`}
                className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
              >
                <div>
                  <p className="font-medium">{index.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {index.identifier} · {index.component_count} components
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium">
                    {index.current_value ? formatCurrency(index.current_value) : '-'}
                  </p>
                  <p className="text-sm text-muted-foreground capitalize">{index.status}</p>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>

      {/* Recent Backtests */}
      <div className="bg-card rounded-xl border">
        <div className="p-6 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Backtests</h2>
          <Link to="/backtests" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </div>
        <div className="divide-y">
          {backtestsLoading ? (
            <div className="p-6 text-center text-muted-foreground">Loading...</div>
          ) : backtests?.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground">
              No backtests yet. Run a backtest from an index detail page.
            </div>
          ) : (
            backtests?.slice(0, 5).map((backtest: any) => (
              <Link
                key={backtest.id}
                to={`/backtests/${backtest.id}`}
                className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
              >
                <div>
                  <p className="font-medium">{backtest.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(backtest.created_at)}
                  </p>
                </div>
                <div className="text-right">
                  {backtest.total_return !== null && (
                    <p
                      className={`font-medium ${
                        backtest.total_return >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}
                    >
                      {formatPercent(backtest.total_return)}
                    </p>
                  )}
                  <p className="text-sm text-muted-foreground capitalize">{backtest.status}</p>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

