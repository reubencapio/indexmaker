import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { backtestsApi } from '@/lib/api'
import { formatPercent, formatDate } from '@/lib/utils'

export function BacktestsPage() {
  const { data: backtests, isLoading } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestsApi.list(),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Backtests</h1>
        <p className="text-muted-foreground">Historical performance analysis of your indices</p>
      </div>

      <div className="bg-card rounded-xl border overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Loading...</div>
        ) : backtests?.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <p>No backtests yet.</p>
            <p className="text-sm">Run a backtest from any index detail page.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Name</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Status</th>
                <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Total Return</th>
                <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Sharpe Ratio</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {backtests?.map((backtest: any) => (
                <tr key={backtest.id} className="hover:bg-muted/50">
                  <td className="px-6 py-4">
                    <Link to={`/backtests/${backtest.id}`} className="font-medium text-primary hover:underline">
                      {backtest.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                      backtest.status === 'completed' ? 'bg-green-100 text-green-700' :
                      backtest.status === 'running' ? 'bg-blue-100 text-blue-700' :
                      backtest.status === 'failed' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {backtest.status}
                    </span>
                  </td>
                  <td className={`px-6 py-4 text-right font-medium ${
                    backtest.total_return >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {backtest.total_return !== null ? formatPercent(backtest.total_return) : '-'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {backtest.sharpe_ratio?.toFixed(2) || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {formatDate(backtest.created_at)}
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

