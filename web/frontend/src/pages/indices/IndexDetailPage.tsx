import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Edit, Trash2, Play, RefreshCw, X, BarChart3, Scale } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { indicesApi, backtestsApi, marketDataProvidersApi, aiApi } from '@/lib/api'
import { formatCurrency, formatPercent, formatMarketCap } from '@/lib/utils'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function IndexDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Backtest dialog state
  const [showBacktestDialog, setShowBacktestDialog] = useState(false)
  const [backtestName, setBacktestName] = useState('')
  const [backtestStartDate, setBacktestStartDate] = useState('')
  const [backtestEndDate, setBacktestEndDate] = useState('')
  const [backtestBenchmark, setBacktestBenchmark] = useState('SPY')

  // Add component dialog state
  const [showAddComponentDialog, setShowAddComponentDialog] = useState(false)
  const [newComponentTicker, setNewComponentTicker] = useState('')
  const [newComponentWeight, setNewComponentWeight] = useState('0.1')

  // Selection criteria dialog state
  const [showCriteriaDialog, setShowCriteriaDialog] = useState(false)
  const [criteriaList, setCriteriaList] = useState<string[]>([])

  // Guideline upload state
  const [isDragging, setIsDragging] = useState(false)

  const { data: index, isLoading } = useQuery({
    queryKey: ['index', id],
    queryFn: () => indicesApi.get(id!),
    enabled: !!id,
    // While the AI builds the index in the background there is nothing to push an
    // update to the client, so poll until it settles into a terminal status.
    refetchInterval: (query) =>
      query.state.data?.status === 'building' ? 3000 : false,
  })

  // Fetch active data source
  const { data: activeDataSource } = useQuery({
    queryKey: ['activeDataSource'],
    queryFn: marketDataProvidersApi.getActive,
  })

  const deleteMutation = useMutation({
    mutationFn: () => indicesApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['indices'] })
      navigate('/indices')
    },
  })

  const calculateMutation = useMutation({
    mutationFn: () => indicesApi.calculate(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
    },
  })

  const regenerateMutation = useMutation({
    mutationFn: () => aiApi.regenerate(id!),
    onSuccess: () => {
      // Flips the index back to "building", which the poll above then follows.
      queryClient.invalidateQueries({ queryKey: ['index', id] })
      queryClient.invalidateQueries({ queryKey: ['indices'] })
    },
  })

  const backtestMutation = useMutation({
    mutationFn: (data: { name: string; start_date: string; end_date: string; benchmark_ticker?: string }) =>
      backtestsApi.create(id!, data),
    onSuccess: (backtest) => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
      setShowBacktestDialog(false)
      navigate(`/backtests/${backtest.id}`)
    },
  })

  const addComponentMutation = useMutation({
    mutationFn: (data: { ticker: string; weight: number }) =>
      indicesApi.addComponent(id!, data.ticker, data.weight),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
      setShowAddComponentDialog(false)
      setNewComponentTicker('')
      setNewComponentWeight('0.1')
    },
  })

  const updateStatusMutation = useMutation({
    mutationFn: (newStatus: string) =>
      indicesApi.update(id!, { status: newStatus }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
      queryClient.invalidateQueries({ queryKey: ['indices'] })
    },
  })

  // Guideline document mutations
  const uploadGuidelineMutation = useMutation({
    mutationFn: (file: File) => indicesApi.uploadGuideline(id!, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
    },
  })

  const deleteGuidelineMutation = useMutation({
    mutationFn: () => indicesApi.deleteGuideline(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
    },
  })

  // Selection criteria mutation
  const updateCriteriaMutation = useMutation({
    mutationFn: (criteria: string[]) =>
      indicesApi.update(id!, { selection_criteria: criteria }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
      setShowCriteriaDialog(false)
    },
  })

  // File upload handlers
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadGuidelineMutation.mutate(file)
    }
  }

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type === 'application/pdf') {
      uploadGuidelineMutation.mutate(file)
    }
  }

  // Generate default selection criteria from index configuration
  const generateDefaultCriteria = () => {
    if (!index) return []
    const criteria: string[] = []

    // Universe/Asset class
    if (index.countries?.length) {
      const countryNames = index.countries.join(', ')
      criteria.push(`Universe consists of equities listed in ${countryNames}`)
    }

    // Minimum market cap
    if (index.min_market_cap) {
      const formattedCap = index.min_market_cap >= 1e9
        ? `$${(index.min_market_cap / 1e9).toFixed(1)}B`
        : `$${(index.min_market_cap / 1e6).toFixed(0)}M`
      criteria.push(`Minimum market capitalization of ${formattedCap}`)
    }

    // Minimum average volume
    if (index.min_avg_volume) {
      criteria.push(`Minimum average daily trading volume of ${index.min_avg_volume.toLocaleString()} shares`)
    }

    // Max components
    if (index.max_components) {
      criteria.push(`Select top ${index.max_components} securities ranked by market capitalization`)
    }

    // Sectors
    if (index.sectors?.length) {
      criteria.push(`Limited to sectors: ${index.sectors.join(', ')}`)
    }

    // Weighting method
    if (index.weighting_method) {
      const methodNames: Record<string, string> = {
        'equal_weight': 'Equal weighted',
        'market_cap': 'Market capitalization weighted',
        'free_float_market_cap': 'Free-float market capitalization weighted',
        'custom': 'Custom weighting scheme'
      }
      const method = methodNames[index.weighting_method] || index.weighting_method.replace(/_/g, ' ')
      criteria.push(`${method} methodology`)
    }

    // Weight caps
    if (index.max_weight) {
      criteria.push(`Maximum individual security weight capped at ${(index.max_weight * 100).toFixed(0)}%`)
    }
    if (index.max_sector_weight) {
      criteria.push(`Maximum sector weight capped at ${(index.max_sector_weight * 100).toFixed(0)}%`)
    }
    if (index.max_country_weight) {
      criteria.push(`Maximum country weight capped at ${(index.max_country_weight * 100).toFixed(0)}%`)
    }

    // Rebalancing
    if (index.rebalance_frequency) {
      const freqNames: Record<string, string> = {
        'daily': 'Daily',
        'weekly': 'Weekly',
        'monthly': 'Monthly',
        'quarterly': 'Quarterly',
        'semi_annual': 'Semi-annual',
        'annual': 'Annual'
      }
      const freq = freqNames[index.rebalance_frequency] || index.rebalance_frequency
      criteria.push(`${freq} rebalancing schedule`)
    }

    return criteria
  }

  const openCriteriaDialog = () => {
    // Use existing criteria, or auto-generate from index config
    const existingCriteria = index?.selection_criteria || []
    setCriteriaList(existingCriteria.length > 0 ? existingCriteria : generateDefaultCriteria())
    setShowCriteriaDialog(true)
  }

  const handleRunBacktest = () => {
    // Set default dates (1 year ago to today)
    const today = new Date()
    const oneYearAgo = new Date()
    oneYearAgo.setFullYear(today.getFullYear() - 1)

    setBacktestName(`${index?.name || 'Index'} Backtest`)
    setBacktestStartDate(oneYearAgo.toISOString().split('T')[0])
    setBacktestEndDate(today.toISOString().split('T')[0])
    setShowBacktestDialog(true)
  }

  const submitBacktest = () => {

    backtestMutation.mutate({
      name: backtestName,
      start_date: backtestStartDate,
      end_date: backtestEndDate,
      benchmark_ticker: backtestBenchmark || undefined,
    })
  }

  const submitAddComponent = () => {

    addComponentMutation.mutate({
      ticker: newComponentTicker.toUpperCase(),
      weight: parseFloat(newComponentWeight),
    })
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  if (!index) {
    return <div className="text-center py-12">Index not found</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/indices" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Indices
          </Link>
          <h1 className="text-3xl font-bold">{index.name}</h1>
          <p className="text-muted-foreground font-mono">{index.identifier}</p>
        </div>
        <div className="flex gap-2">
          <Link to={`/indices/${id}/analytics`}>
            <Button variant="outline" className="bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-200 hover:from-emerald-100 hover:to-teal-100">
              <BarChart3 className="h-4 w-4 mr-2 text-emerald-600" />
              Analytics
            </Button>
          </Link>
          <Link to={`/indices/${id}/rebalancing`}>
            <Button variant="outline" className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 hover:from-blue-100 hover:to-indigo-100">
              <Scale className="h-4 w-4 mr-2 text-blue-600" />
              Rebalancing
            </Button>
          </Link>
          <Button variant="outline" onClick={() => calculateMutation.mutate()} disabled={calculateMutation.isPending}>
            <RefreshCw className={`h-4 w-4 mr-2 ${calculateMutation.isPending ? 'animate-spin' : ''}`} />
            Calculate
          </Button>
          <Link to={`/indices/${id}/edit`}>
            <Button variant="outline">
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
          </Link>
          <Button variant="destructive" onClick={() => deleteMutation.mutate()}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-4 gap-4">
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Current Value</p>
          <p className="text-2xl font-bold">
            {index.current_value ? formatCurrency(index.current_value) : '-'}
          </p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Components</p>
          <p className="text-2xl font-bold">{index.component_count}</p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Weighting</p>
          <p className="text-lg font-medium capitalize">{index.weighting_method.replace('_', ' ')}</p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground mb-2">Status</p>
          {/* "building" and "error" are task-driven, not user-editable: rendering the
              dropdown for them would silently fall back to its first option ("Draft")
              because neither value matches any <option>. */}
          {index.status === 'building' ? (
            <span className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg border-2 bg-purple-50 border-purple-200 text-purple-700">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Building…
            </span>
          ) : index.status === 'error' ? (
            <span className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg border-2 bg-red-50 border-red-200 text-red-700">
              <X className="w-3.5 h-3.5" />
              Failed
            </span>
          ) : (
            <select
              value={index.status}
              onChange={(e) => updateStatusMutation.mutate(e.target.value)}
              disabled={updateStatusMutation.isPending}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg border-2 focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer ${index.status === 'active'
                ? 'bg-green-50 border-green-200 text-green-700'
                : index.status === 'draft'
                  ? 'bg-yellow-50 border-yellow-200 text-yellow-700'
                  : index.status === 'paused'
                    ? 'bg-gray-50 border-gray-200 text-gray-700'
                    : 'bg-gray-50 border-gray-200 text-gray-700'
                } ${updateStatusMutation.isPending ? 'opacity-50' : ''}`}
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="archived">Archived</option>
            </select>
          )}
        </div>
      </div>

      {/* Generation state banner. The methodology and code panels below are rendered
          from the stored config, which is still empty until generation succeeds --
          so say that plainly rather than letting defaults read as real settings. */}
      {index.status === 'building' && (
        <div className="rounded-xl border border-purple-200 bg-purple-50 dark:bg-purple-950/30 dark:border-purple-900 p-6">
          <div className="flex items-start gap-3">
            <RefreshCw className="w-5 h-5 mt-0.5 text-purple-600 animate-spin shrink-0" />
            <div>
              <h2 className="font-semibold text-purple-900 dark:text-purple-200">
                Building your index…
              </h2>
              <p className="text-sm text-purple-800/80 dark:text-purple-300/80 mt-1">
                The AI is selecting constituents and building the methodology. This
                usually takes under a minute. This page updates automatically.
              </p>
            </div>
          </div>
        </div>
      )}

      {index.status === 'error' && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900 p-6">
          <div className="flex items-start gap-3">
            <X className="w-5 h-5 mt-0.5 text-red-600 shrink-0" />
            <div className="flex-1">
              <h2 className="font-semibold text-red-900 dark:text-red-200">
                Index generation failed
              </h2>
              <p className="text-sm text-red-800/80 dark:text-red-300/80 mt-1">
                {index.error_message ||
                  'The AI could not generate this index. No settings were saved, so the methodology shown below is empty defaults.'}
              </p>
              {/* Retry reuses the stored prompt. Indices created before prompts were
                  persisted have none, so they fall back to starting over. */}
              {index.generation_prompt ? (
                <div className="mt-3 flex items-center gap-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => regenerateMutation.mutate()}
                    disabled={regenerateMutation.isPending}
                  >
                    <RefreshCw
                      className={`w-3.5 h-3.5 mr-1.5 ${regenerateMutation.isPending ? 'animate-spin' : ''}`}
                    />
                    {regenerateMutation.isPending ? 'Retrying…' : 'Retry generation'}
                  </Button>
                  <span className="text-xs text-red-800/60 dark:text-red-300/60 truncate">
                    “{index.generation_prompt}”
                  </span>
                </div>
              ) : (
                <Link
                  to="/indices/new"
                  className="inline-block mt-3 text-sm font-medium text-red-700 dark:text-red-300 hover:underline"
                >
                  Try creating it again →
                </Link>
              )}
              {regenerateMutation.isError && (
                <p className="text-xs text-red-700 dark:text-red-300 mt-2">
                  Could not start a retry. Please try again in a moment.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Description */}
      {index.description && (
        <div className="bg-card rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-2">Description</h2>
          <p className="text-muted-foreground">{index.description}</p>
        </div>
      )}

      {/* Index Methodology Section */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Selection Criteria */}
        <div className="bg-card rounded-xl border p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Selection Criteria
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={openCriteriaDialog}
              className="text-blue-600 hover:text-blue-700"
            >
              <Edit className="h-4 w-4 mr-1" />
              Edit
            </Button>
          </div>
          {(() => {
            const displayCriteria = index.selection_criteria?.length > 0
              ? index.selection_criteria
              : generateDefaultCriteria()
            const isAutoGenerated = !index.selection_criteria?.length

            return displayCriteria.length > 0 ? (
              <div>
                {isAutoGenerated && (
                  <p className="text-xs text-blue-600 mb-3 flex items-center gap-1">
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    Auto-generated from index configuration. Click Edit to customize.
                  </p>
                )}
                <ol className="space-y-3">
                  {displayCriteria.map((criterion: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-medium">
                        {idx + 1}
                      </span>
                      <span className="text-sm text-muted-foreground pt-0.5">{criterion}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground">
                <svg className="h-10 w-10 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                <p className="text-sm">No selection criteria defined</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={openCriteriaDialog}
                >
                  Add Criteria
                </Button>
              </div>
            )
          })()}
        </div>

        {/* Guideline Document */}
        <div className="bg-card rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 24 24">
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M10,19L12,15H9V10H15V15L13,19H10Z" />
            </svg>
            Index Guideline Document
          </h2>
          {index.guideline_file_name ? (
            <div className="border rounded-lg p-4 bg-gradient-to-r from-red-50 to-orange-50">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-red-100 flex items-center justify-center">
                  <svg className="h-6 w-6 text-red-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{index.guideline_file_name}</p>
                  <p className="text-xs text-muted-foreground">PDF Document</p>
                </div>
                <div className="flex gap-2">
                  <a
                    href={`${API_URL}${index.guideline_file_url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                  >
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download
                  </a>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteGuidelineMutation.mutate()}
                    disabled={deleteGuidelineMutation.isPending}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                }`}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleFileDrop}
            >
              <svg className="h-10 w-10 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-sm text-muted-foreground mb-2">
                Drag and drop a PDF file, or
              </p>
              <label className="inline-flex items-center px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors cursor-pointer">
                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Browse Files
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={handleFileSelect}
                  disabled={uploadGuidelineMutation.isPending}
                />
              </label>
              <p className="text-xs text-muted-foreground mt-2">PDF only, max 10MB</p>
              {uploadGuidelineMutation.isPending && (
                <p className="text-sm text-blue-600 mt-2 animate-pulse">Uploading...</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Components */}
      <div className="bg-card rounded-xl border overflow-hidden">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold">Components</h2>
            <Link
              to="/data-sources"
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-purple-100 text-purple-700 text-xs font-medium hover:bg-purple-200 transition-colors"
              title="Click to change data source"
            >
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
              </svg>
              Data: {activeDataSource?.name || 'Yahoo Finance'}
            </Link>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAddComponentDialog(true)}
            >
              + Add Component
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRunBacktest}
              disabled={!index?.components?.length}
              title={!index?.components?.length ? 'Add components first' : ''}
            >
              <Play className="h-4 w-4 mr-2" />
              Run Backtest
            </Button>
          </div>
        </div>
        {index.components?.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            No components added yet
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Ticker</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Name</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Sector</th>
                <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Market Cap</th>
                <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Weight</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {index.components?.map((component: any) => (
                <tr key={component.id} className="hover:bg-muted/50">
                  <td className="px-6 py-4 font-mono font-medium">{component.ticker}</td>
                  <td className="px-6 py-4">{component.name || '-'}</td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">{component.sector || '-'}</td>
                  <td className="px-6 py-4 text-right">{component.market_cap ? formatMarketCap(component.market_cap) : '-'}</td>
                  <td className="px-6 py-4 text-right font-medium">{formatPercent(component.weight)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Backtest Dialog */}
      {showBacktestDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Run Backtest</h2>
              <button onClick={() => setShowBacktestDialog(false)} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Backtest Name</label>
                <input
                  type="text"
                  value={backtestName}
                  onChange={(e) => setBacktestName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="My Backtest"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={backtestStartDate}
                    onChange={(e) => setBacktestStartDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                  <input
                    type="date"
                    value={backtestEndDate}
                    onChange={(e) => setBacktestEndDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Benchmark (optional)</label>
                <input
                  type="text"
                  value={backtestBenchmark}
                  onChange={(e) => setBacktestBenchmark(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="SPY"
                />
                <p className="text-xs text-gray-500 mt-1">Enter a ticker symbol to compare against (e.g., SPY, QQQ)</p>
              </div>

              {backtestMutation.isError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">
                  {(backtestMutation.error as any)?.response?.data?.detail || 'Failed to create backtest'}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowBacktestDialog(false)}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={submitBacktest}
                  disabled={backtestMutation.isPending || !backtestName || !backtestStartDate || !backtestEndDate}
                >
                  {backtestMutation.isPending ? 'Running...' : 'Run Backtest'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Component Dialog */}
      {showAddComponentDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Add Component</h2>
              <button onClick={() => setShowAddComponentDialog(false)} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ticker Symbol</label>
                <input
                  type="text"
                  value={newComponentTicker}
                  onChange={(e) => setNewComponentTicker(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 uppercase"
                  placeholder="AAPL"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Weight</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={newComponentWeight}
                  onChange={(e) => setNewComponentWeight(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">Enter as decimal (e.g., 0.10 for 10%)</p>
              </div>

              {addComponentMutation.isError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">
                  {(addComponentMutation.error as any)?.response?.data?.detail || 'Failed to add component'}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowAddComponentDialog(false)}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={submitAddComponent}
                  disabled={addComponentMutation.isPending || !newComponentTicker}
                >
                  {addComponentMutation.isPending ? 'Adding...' : 'Add Component'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Selection Criteria Dialog */}
      {showCriteriaDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Edit Selection Criteria</h2>
              <button onClick={() => setShowCriteriaDialog(false)} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-sm text-muted-foreground mb-4">
              Define the rules and criteria used to select components for this index.
            </p>

            <div className="space-y-3 mb-4">
              {criteriaList.map((criterion, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-medium">
                    {idx + 1}
                  </span>
                  <input
                    type="text"
                    value={criterion}
                    onChange={(e) => {
                      const newList = [...criteriaList]
                      newList[idx] = e.target.value
                      setCriteriaList(newList)
                    }}
                    className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder={`Criterion ${idx + 1}`}
                  />
                  <button
                    onClick={() => {
                      setCriteriaList(criteriaList.filter((_, i) => i !== idx))
                    }}
                    className="text-red-500 hover:text-red-700 p-1"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="flex gap-2 mb-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCriteriaList([...criteriaList, ''])}
                className="flex-1"
              >
                + Add Criterion
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCriteriaList(generateDefaultCriteria())}
                className="text-blue-600 hover:text-blue-700"
                title="Regenerate from index configuration"
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                Regenerate
              </Button>
            </div>

            {updateCriteriaMutation.isError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm mb-4">
                Failed to save criteria
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowCriteriaDialog(false)}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                onClick={() => updateCriteriaMutation.mutate(criteriaList.filter(c => c.trim() !== ''))}
                disabled={updateCriteriaMutation.isPending}
              >
                {updateCriteriaMutation.isPending ? 'Saving...' : 'Save Criteria'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
