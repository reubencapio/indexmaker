import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, AlertCircle, Loader2, ExternalLink, Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { marketDataProvidersApi, MarketDataSource } from '@/lib/api'
import { toast } from 'sonner'

export function MarketDataProviderSettings() {
  const queryClient = useQueryClient()
  const [apiKeyInput, setApiKeyInput] = useState<Record<string, string>>({})
  const [testingProvider, setTestingProvider] = useState<string | null>(null)

  // Fetch available data sources
  const { data, isLoading } = useQuery({
    queryKey: ['marketDataProviders'],
    queryFn: marketDataProvidersApi.list,
  })

  // Set active data source mutation
  const setActiveMutation = useMutation({
    mutationFn: ({ sourceId, apiKey }: { sourceId: string; apiKey?: string }) =>
      marketDataProvidersApi.setActive(sourceId, apiKey),
    onSuccess: (result) => {
      if (result.is_connected) {
        queryClient.invalidateQueries({ queryKey: ['marketDataProviders'] })
        toast.success('Data source updated', {
          description: result.message,
        })
      } else {
        toast.error('Connection failed', {
          description: result.message,
        })
      }
    },
    onError: (error: any) => {
      toast.error('Failed to set data source', {
        description: error?.response?.data?.detail || 'Something went wrong',
      })
    },
  })

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: ({ sourceId, apiKey }: { sourceId: string; apiKey?: string }) =>
      marketDataProvidersApi.test(sourceId, apiKey),
    onSuccess: (result) => {
      setTestingProvider(null)
      if (result.is_connected) {
        toast.success('Connection successful!', {
          description: result.message,
        })
      } else {
        toast.error('Connection failed', {
          description: result.message,
        })
      }
    },
    onError: (error: any) => {
      setTestingProvider(null)
      toast.error('Test failed', {
        description: error?.response?.data?.detail || 'Could not test connection',
      })
    },
  })

  const handleSelectProvider = (source: MarketDataSource) => {
    if (source.requires_api_key && !apiKeyInput[source.id]) {
      toast.error('API Key Required', {
        description: `Please enter an API key for ${source.name}`,
      })
      return
    }
    setActiveMutation.mutate({
      sourceId: source.id,
      apiKey: apiKeyInput[source.id],
    })
  }

  const handleTestConnection = (source: MarketDataSource) => {
    setTestingProvider(source.id)
    testMutation.mutate({
      sourceId: source.id,
      apiKey: apiKeyInput[source.id],
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const activeSource = data?.active_source || 'yahoo'
  const sources = data?.sources || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Database className="h-5 w-5" />
          Market Data Provider
        </h2>
        <p className="text-muted-foreground mt-1">
          Choose where to source real-time and historical market data for your indices.
        </p>
      </div>

      {/* Provider Cards */}
      <div className="grid gap-4">
        {sources.map((source) => {
          const isActive = source.id === activeSource
          const isSelecting = setActiveMutation.isPending && setActiveMutation.variables?.sourceId === source.id
          const isTesting = testingProvider === source.id

          return (
            <div
              key={source.id}
              className={`relative rounded-xl border-2 transition-all ${
                isActive
                  ? 'border-green-500 bg-green-50/50'
                  : source.is_available
                    ? 'border-gray-200 hover:border-gray-300'
                    : 'border-gray-100 bg-gray-50/50 opacity-60'
              }`}
            >
              {/* Active Badge */}
              {isActive && (
                <div className="absolute -top-3 left-4 px-2 py-0.5 bg-green-500 text-white text-xs font-medium rounded-full flex items-center gap-1">
                  <Check className="h-3 w-3" />
                  Active
                </div>
              )}

              <div className="p-5">
                <div className="flex items-start gap-4">
                  {/* Logo */}
                  <div className="flex-shrink-0">
                    {source.logo ? (
                      <img
                        src={source.logo}
                        alt={source.name}
                        className="h-12 w-12 rounded-lg object-contain bg-white border p-1"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none'
                        }}
                      />
                    ) : (
                      <div className="h-12 w-12 rounded-lg bg-gray-100 flex items-center justify-center">
                        <Database className="h-6 w-6 text-gray-400" />
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-lg">{source.name}</h3>
                      {!source.is_available && (
                        <span className="px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded-full">
                          Coming Soon
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {source.description}
                    </p>

                    {/* Features */}
                    <div className="flex flex-wrap gap-2 mt-3">
                      {source.features.map((feature) => (
                        <span
                          key={feature}
                          className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full"
                        >
                          {feature.replace('_', ' ')}
                        </span>
                      ))}
                    </div>

                    {/* Limitations */}
                    {source.limitations.length > 0 && (
                      <div className="flex items-start gap-2 mt-3 text-sm text-amber-700">
                        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                        <span>{source.limitations.join(' • ')}</span>
                      </div>
                    )}

                    {/* API Key Input (if required) */}
                    {source.requires_api_key && source.is_available && (
                      <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          API Key
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="password"
                            value={apiKeyInput[source.id] || ''}
                            onChange={(e) =>
                              setApiKeyInput((prev) => ({
                                ...prev,
                                [source.id]: e.target.value,
                              }))
                            }
                            placeholder="Enter your API key"
                            className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                          />
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleTestConnection(source)}
                            disabled={!apiKeyInput[source.id] || isTesting}
                          >
                            {isTesting ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              'Test'
                            )}
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Action Button */}
                  <div className="flex-shrink-0">
                    {source.is_available ? (
                      isActive ? (
                        <Button variant="outline" size="sm" disabled>
                          <Check className="h-4 w-4 mr-1" />
                          Selected
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => handleSelectProvider(source)}
                          disabled={isSelecting}
                        >
                          {isSelecting ? (
                            <Loader2 className="h-4 w-4 animate-spin mr-1" />
                          ) : null}
                          {isSelecting ? 'Connecting...' : 'Use This'}
                        </Button>
                      )
                    ) : (
                      <Button variant="outline" size="sm" disabled>
                        Unavailable
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">About Data Sources</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>
            • <strong>Yahoo Finance:</strong> Free, no API key needed. Great for getting started.
          </li>
          <li>
            • <strong>OpenBB:</strong> Open-source platform with stock screening capabilities.
          </li>
          <li>
            • <strong>FMP & Polygon:</strong> Premium features with higher rate limits (coming soon).
          </li>
        </ul>
        <a
          href="https://openbb.co/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline mt-3"
        >
          Learn more about OpenBB
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  )
}

