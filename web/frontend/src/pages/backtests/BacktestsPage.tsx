import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { backtestsApi, indicesApi, CreateBacktestRequest } from '@/lib/api'
import { formatPercent, formatDate } from '@/lib/utils'
import { toast } from 'sonner'

export function BacktestsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [selectedIndexId, setSelectedIndexId] = useState('')
  const [formData, setFormData] = useState({
    name: '',
    start_date: '',
    end_date: '',
    initial_value: 10000,
    benchmark_ticker: 'SPY',
  })

  const { data: backtests, isLoading } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestsApi.list(),
  })

  const { data: indices } = useQuery({
    queryKey: ['indices'],
    queryFn: () => indicesApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: (data: CreateBacktestRequest) => backtestsApi.create(selectedIndexId, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
      toast.success('Backtest created successfully!')
      setShowModal(false)
      navigate(`/backtests/${result.id}`)
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to create backtest')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedIndexId) {
      toast.error('Please select an index')
      return
    }
    createMutation.mutate(formData)
  }

  const handleIndexChange = (indexId: string) => {
    setSelectedIndexId(indexId)
    const selectedIndex = indices?.find((idx: any) => idx.id === indexId)
    if (selectedIndex) {
      setFormData(prev => ({
        ...prev,
        name: `${selectedIndex.name} Backtest`,
      }))
    }
  }

  // Set default dates (last 2 years)
  const getDefaultDates = () => {
    const end = new Date()
    const start = new Date()
    start.setFullYear(start.getFullYear() - 2)
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
    }
  }

  const openModal = () => {
    const dates = getDefaultDates()
    setFormData(prev => ({
      ...prev,
      start_date: dates.start,
      end_date: dates.end,
    }))
    setShowModal(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Backtests</h1>
          <p className="text-muted-foreground">Historical performance analysis of your indices</p>
        </div>
        <button
          onClick={openModal}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Backtest
        </button>
      </div>

      <div className="bg-card rounded-xl border overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Loading...</div>
        ) : backtests?.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <p>No backtests yet.</p>
            <p className="text-sm mt-2">Click "New Backtest" to run your first backtest.</p>
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
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${backtest.status === 'completed' ? 'bg-green-100 text-green-700' :
                        backtest.status === 'running' ? 'bg-blue-100 text-blue-700' :
                          backtest.status === 'failed' ? 'bg-red-100 text-red-700' :
                            'bg-yellow-100 text-yellow-700'
                      }`}>
                      {backtest.status}
                    </span>
                  </td>
                  <td className={`px-6 py-4 text-right font-medium ${backtest.total_return >= 0 ? 'text-green-500' : 'text-red-500'
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

      {/* New Backtest Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-xl border shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Create New Backtest</h2>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Select Index *</label>
                <select
                  value={selectedIndexId}
                  onChange={(e) => handleIndexChange(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                  required
                >
                  <option value="">Choose an index...</option>
                  {indices?.map((index: any) => (
                    <option key={index.id} value={index.id}>
                      {index.name} ({index.identifier})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Backtest Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                  placeholder="My Backtest"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Start Date *</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">End Date *</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Initial Value</label>
                  <input
                    type="number"
                    value={formData.initial_value}
                    onChange={(e) => setFormData({ ...formData, initial_value: Number(e.target.value) })}
                    className="w-full px-3 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                    min={100}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Benchmark</label>
                  <input
                    type="text"
                    value={formData.benchmark_ticker}
                    onChange={(e) => setFormData({ ...formData, benchmark_ticker: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                    placeholder="SPY"
                  />
                  <p className="text-xs text-muted-foreground mt-1">e.g., SPY, QQQ, IWM</p>
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || !selectedIndexId}
                  className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Backtest'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
