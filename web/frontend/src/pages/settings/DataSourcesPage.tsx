import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Database, Upload, Trash2, ChevronRight, X, Globe, Server, RefreshCw, CheckCircle, AlertCircle, FileSpreadsheet } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { dataSourcesApi, SecurityData, CSVColumnMapping } from '@/lib/api'
import { formatDate } from '@/lib/utils'

type SourceType = 'ticker_list' | 'csv_upload' | 'api_endpoint' | 'database'

export function DataSourcesPage() {
  const queryClient = useQueryClient()
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showAddSecuritiesDialog, setShowAddSecuritiesDialog] = useState<string | null>(null)
  const [selectedDataSource, setSelectedDataSource] = useState<string | null>(null)

  const { data: dataSources, isLoading } = useQuery({
    queryKey: ['dataSources'],
    queryFn: () => dataSourcesApi.list(),
  })

  const { data: selectedSourceDetails } = useQuery({
    queryKey: ['dataSource', selectedDataSource],
    queryFn: () => dataSourcesApi.get(selectedDataSource!),
    enabled: !!selectedDataSource,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => dataSourcesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] })
      setSelectedDataSource(null)
    },
  })

  const syncAPIMutation = useMutation({
    mutationFn: (id: string) => dataSourcesApi.syncFromAPI(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSource', selectedDataSource] })
      queryClient.invalidateQueries({ queryKey: ['dataSources'] })
    },
  })

  const syncDatabaseMutation = useMutation({
    mutationFn: (id: string) => dataSourcesApi.syncFromDatabase(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSource', selectedDataSource] })
      queryClient.invalidateQueries({ queryKey: ['dataSources'] })
    },
  })

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'api_endpoint':
        return <Globe className="h-5 w-5 text-green-600" />
      case 'database':
        return <Server className="h-5 w-5 text-purple-600" />
      case 'csv_upload':
        return <FileSpreadsheet className="h-5 w-5 text-orange-600" />
      default:
        return <Database className="h-5 w-5 text-blue-600" />
    }
  }

  const getSourceColor = (type: string) => {
    switch (type) {
      case 'api_endpoint':
        return 'bg-green-100'
      case 'database':
        return 'bg-purple-100'
      case 'csv_upload':
        return 'bg-orange-100'
      default:
        return 'bg-blue-100'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Data Sources</h1>
          <p className="text-muted-foreground">
            Connect your own securities database, API, or upload custom data
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Data Source
        </Button>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Data Sources List */}
        <div className="md:col-span-1 space-y-4">
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : dataSources?.length === 0 ? (
            <div className="bg-card rounded-xl border p-8 text-center">
              <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="font-medium mb-2">No data sources yet</p>
              <p className="text-sm text-muted-foreground mb-4">
                Create a custom data source to use your own securities database
              </p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Data Source
              </Button>
            </div>
          ) : (
            dataSources?.map((source: any) => (
              <button
                key={source.id}
                onClick={() => setSelectedDataSource(source.id)}
                className={`w-full text-left bg-card rounded-xl border p-4 hover:border-primary transition-colors ${selectedDataSource === source.id ? 'border-primary ring-2 ring-primary/20' : ''
                  }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`h-10 w-10 rounded-lg ${getSourceColor(source.source_type)} flex items-center justify-center`}>
                      {getSourceIcon(source.source_type)}
                    </div>
                    <div>
                      <p className="font-medium">{source.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {source.securities_count} securities • {source.source_type.replace('_', ' ')}
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground" />
                </div>
              </button>
            ))
          )}
        </div>

        {/* Selected Data Source Details */}
        <div className="md:col-span-2">
          {selectedDataSource && selectedSourceDetails ? (
            <div className="bg-card rounded-xl border">
              <div className="p-6 border-b">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`h-12 w-12 rounded-lg ${getSourceColor(selectedSourceDetails.source_type)} flex items-center justify-center`}>
                      {getSourceIcon(selectedSourceDetails.source_type)}
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold">{selectedSourceDetails.name}</h2>
                      <p className="text-sm text-muted-foreground">
                        {selectedSourceDetails.description || selectedSourceDetails.source_type.replace('_', ' ')}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {selectedSourceDetails.source_type === 'api_endpoint' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => syncAPIMutation.mutate(selectedDataSource)}
                        disabled={syncAPIMutation.isPending}
                      >
                        <RefreshCw className={`h-4 w-4 mr-2 ${syncAPIMutation.isPending ? 'animate-spin' : ''}`} />
                        Sync from API
                      </Button>
                    )}
                    {selectedSourceDetails.source_type === 'database' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => syncDatabaseMutation.mutate(selectedDataSource)}
                        disabled={syncDatabaseMutation.isPending}
                      >
                        <RefreshCw className={`h-4 w-4 mr-2 ${syncDatabaseMutation.isPending ? 'animate-spin' : ''}`} />
                        Sync from DB
                      </Button>
                    )}
                    {(selectedSourceDetails.source_type === 'ticker_list' || selectedSourceDetails.source_type === 'csv_upload') && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowAddSecuritiesDialog(selectedDataSource)}
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Add Securities
                      </Button>
                    )}
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => {
                        if (confirm('Delete this data source and all its securities?')) {
                          deleteMutation.mutate(selectedDataSource)
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Sync Status */}
              {(syncAPIMutation.isSuccess || syncDatabaseMutation.isSuccess) && (
                <div className="mx-6 mt-4 p-3 bg-green-50 text-green-700 rounded-lg flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  <span className="text-sm">
                    Sync complete! Added {(syncAPIMutation.data || syncDatabaseMutation.data)?.added || 0},
                    updated {(syncAPIMutation.data || syncDatabaseMutation.data)?.updated || 0} securities.
                  </span>
                </div>
              )}
              {(syncAPIMutation.isError || syncDatabaseMutation.isError) && (
                <div className="mx-6 mt-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-sm">
                    {(syncAPIMutation.error as any)?.response?.data?.detail ||
                      (syncDatabaseMutation.error as any)?.response?.data?.detail ||
                      'Sync failed'}
                  </span>
                </div>
              )}

              <div className="p-6">
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="bg-muted/50 rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">Securities</p>
                    <p className="text-2xl font-bold">{selectedSourceDetails.securities_count}</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">Type</p>
                    <p className="font-medium capitalize">
                      {selectedSourceDetails.source_type?.replace('_', ' ')}
                    </p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">Last Synced</p>
                    <p className="font-medium">
                      {selectedSourceDetails.last_synced
                        ? formatDate(selectedSourceDetails.last_synced)
                        : 'Never'}
                    </p>
                  </div>
                </div>

                {/* Configuration Details */}
                {(selectedSourceDetails.source_type === 'api_endpoint' || selectedSourceDetails.source_type === 'database') && (
                  <div className="mb-6 p-4 bg-muted/30 rounded-lg">
                    <h3 className="font-semibold mb-2">Configuration</h3>
                    {selectedSourceDetails.source_type === 'api_endpoint' && (
                      <div className="text-sm space-y-1">
                        <p><span className="text-muted-foreground">Endpoint:</span> {selectedSourceDetails.config?.endpoint}</p>
                        <p><span className="text-muted-foreground">Method:</span> {selectedSourceDetails.config?.method || 'GET'}</p>
                        {selectedSourceDetails.config?.response_path && (
                          <p><span className="text-muted-foreground">Response Path:</span> {selectedSourceDetails.config.response_path}</p>
                        )}
                      </div>
                    )}
                    {selectedSourceDetails.source_type === 'database' && (
                      <div className="text-sm space-y-1">
                        <p><span className="text-muted-foreground">Type:</span> {selectedSourceDetails.config?.db_type}</p>
                        <p><span className="text-muted-foreground">Host:</span> {selectedSourceDetails.config?.host}:{selectedSourceDetails.config?.port}</p>
                        <p><span className="text-muted-foreground">Database:</span> {selectedSourceDetails.config?.database}</p>
                      </div>
                    )}
                  </div>
                )}

                <h3 className="font-semibold mb-4">Securities</h3>
                {selectedSourceDetails.securities?.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No securities added yet
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="text-left px-4 py-2 text-sm font-medium">Ticker</th>
                          <th className="text-left px-4 py-2 text-sm font-medium">Name</th>
                          <th className="text-left px-4 py-2 text-sm font-medium">Sector</th>
                          <th className="text-left px-4 py-2 text-sm font-medium">Country</th>
                          <th className="text-right px-4 py-2 text-sm font-medium">Market Cap</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {selectedSourceDetails.securities?.slice(0, 20).map((security: any) => (
                          <tr key={security.id}>
                            <td className="px-4 py-2 font-mono font-medium">{security.ticker}</td>
                            <td className="px-4 py-2">{security.name || '-'}</td>
                            <td className="px-4 py-2 text-sm text-muted-foreground">
                              {security.sector || '-'}
                            </td>
                            <td className="px-4 py-2">{security.country || '-'}</td>
                            <td className="px-4 py-2 text-right">
                              {security.market_cap
                                ? `$${(security.market_cap / 1e9).toFixed(1)}B`
                                : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {selectedSourceDetails.securities?.length > 20 && (
                      <p className="text-center text-sm text-muted-foreground py-4">
                        Showing 20 of {selectedSourceDetails.securities.length} securities
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-card rounded-xl border p-12 text-center">
              <Database className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">Select a Data Source</h3>
              <p className="text-muted-foreground">
                Choose a data source from the list to view and manage its securities
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Create Data Source Dialog */}
      {showCreateDialog && (
        <CreateDataSourceDialog
          onClose={() => setShowCreateDialog(false)}
          onCreated={(id) => {
            setShowCreateDialog(false)
            setSelectedDataSource(id)
          }}
        />
      )}

      {/* Add Securities Dialog */}
      {showAddSecuritiesDialog && (
        <AddSecuritiesDialog
          dataSourceId={showAddSecuritiesDialog}
          onClose={() => setShowAddSecuritiesDialog(null)}
        />
      )}
    </div>
  )
}

function CreateDataSourceDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const queryClient = useQueryClient()
  const [step, setStep] = useState<'type' | 'config'>('type')
  const [sourceType, setSourceType] = useState<SourceType>('ticker_list')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  // API config
  const [apiEndpoint, setApiEndpoint] = useState('')
  const [apiMethod, setApiMethod] = useState<'GET' | 'POST'>('GET')
  const [apiHeaders, setApiHeaders] = useState('')
  const [apiResponsePath, setApiResponsePath] = useState('')

  // Database config
  const [dbType, setDbType] = useState<'postgresql' | 'mysql'>('postgresql')
  const [dbHost, setDbHost] = useState('')
  const [dbPort, setDbPort] = useState('')
  const [dbName, setDbName] = useState('')
  const [dbUsername, setDbUsername] = useState('')
  const [dbPassword, setDbPassword] = useState('')
  const [dbQuery, setDbQuery] = useState('')

  // Field mapping
  const [tickerField, setTickerField] = useState('ticker')
  const [nameField, setNameField] = useState('name')
  const [sectorField, setSectorField] = useState('sector')
  const [marketCapField, setMarketCapField] = useState('market_cap')

  const [testResult, setTestResult] = useState<{ success: boolean; message?: string; error?: string } | null>(null)

  const testAPIMutation = useMutation({
    mutationFn: () => dataSourcesApi.testAPIConnection({
      endpoint: apiEndpoint,
      method: apiMethod,
      headers: apiHeaders ? JSON.parse(apiHeaders) : undefined,
    }),
    onSuccess: (data) => setTestResult(data),
    onError: (err: any) => setTestResult({ success: false, error: err?.response?.data?.detail || 'Test failed' }),
  })

  const testDBMutation = useMutation({
    mutationFn: () => dataSourcesApi.testDatabaseConnection({
      db_type: dbType,
      host: dbHost,
      port: dbPort ? parseInt(dbPort) : undefined,
      database: dbName,
      username: dbUsername,
      password: dbPassword,
    }),
    onSuccess: (data) => setTestResult(data),
    onError: (err: any) => setTestResult({ success: false, error: err?.response?.data?.detail || 'Test failed' }),
  })

  const createMutation = useMutation({
    mutationFn: () => {
      let config: any = undefined
      let fieldMapping: any = undefined

      if (sourceType === 'api_endpoint') {
        config = {
          endpoint: apiEndpoint,
          method: apiMethod,
          headers: apiHeaders ? JSON.parse(apiHeaders) : undefined,
          response_path: apiResponsePath || undefined,
        }
        fieldMapping = {
          ticker: tickerField,
          name: nameField,
          sector: sectorField,
          market_cap: marketCapField,
        }
      } else if (sourceType === 'database') {
        config = {
          db_type: dbType,
          host: dbHost,
          port: dbPort ? parseInt(dbPort) : (dbType === 'postgresql' ? 5432 : 3306),
          database: dbName,
          username: dbUsername,
          password: dbPassword,
          query: dbQuery,
        }
        fieldMapping = {
          ticker: tickerField,
          name: nameField,
          sector: sectorField,
          market_cap: marketCapField,
        }
      }

      return dataSourcesApi.create({
        name,
        description: description || undefined,
        source_type: sourceType,
        config,
        field_mapping: fieldMapping,
      })
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] })
      onCreated(data.id)
    },
  })

  const sourceTypes = [
    { id: 'ticker_list', name: 'Ticker List', icon: Database, color: 'bg-blue-100 text-blue-600', desc: 'Manually add ticker symbols' },
    { id: 'csv_upload', name: 'CSV Upload', icon: FileSpreadsheet, color: 'bg-orange-100 text-orange-600', desc: 'Import from any CSV file' },
    { id: 'api_endpoint', name: 'API Endpoint', icon: Globe, color: 'bg-green-100 text-green-600', desc: 'Connect to REST API' },
    { id: 'database', name: 'Database', icon: Server, color: 'bg-purple-100 text-purple-600', desc: 'Connect to PostgreSQL/MySQL' },
  ]

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto py-8">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">
            {step === 'type' ? 'Choose Data Source Type' : `Configure ${sourceTypes.find(t => t.id === sourceType)?.name}`}
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
          {step === 'type' ? (
            <div className="grid grid-cols-2 gap-4">
              {sourceTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => {
                    setSourceType(type.id as SourceType)
                    setStep('config')
                  }}
                  className="p-4 border rounded-xl text-left hover:border-primary hover:bg-primary/5 transition-colors"
                >
                  <div className={`h-10 w-10 rounded-lg ${type.color} flex items-center justify-center mb-3`}>
                    <type.icon className="h-5 w-5" />
                  </div>
                  <p className="font-medium">{type.name}</p>
                  <p className="text-sm text-muted-foreground">{type.desc}</p>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Common fields */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="My Data Source"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Optional description"
                />
              </div>

              {/* Simple types just need name */}
              {(sourceType === 'ticker_list' || sourceType === 'csv_upload') && (
                <div className="pt-4 border-t">
                  <div className="bg-blue-50 text-blue-700 p-4 rounded-lg">
                    <p className="font-medium mb-1">
                      {sourceType === 'ticker_list' ? '📋 Ticker List' : '📁 CSV Upload'}
                    </p>
                    <p className="text-sm">
                      {sourceType === 'ticker_list'
                        ? "After creating, you can add ticker symbols manually."
                        : "After creating, you can upload any CSV file and map its columns to our fields."}
                    </p>
                  </div>
                </div>
              )}

              {/* API Endpoint Config */}
              {sourceType === 'api_endpoint' && (
                <>
                  <div className="pt-4 border-t">
                    <h3 className="font-medium mb-3">API Configuration</h3>
                    <div className="grid grid-cols-4 gap-4">
                      <div className="col-span-3">
                        <label className="block text-sm font-medium text-gray-700 mb-1">Endpoint URL *</label>
                        <input
                          type="url"
                          value={apiEndpoint}
                          onChange={(e) => setApiEndpoint(e.target.value)}
                          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          placeholder="https://api.example.com/securities"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Method</label>
                        <select
                          value={apiMethod}
                          onChange={(e) => setApiMethod(e.target.value as 'GET' | 'POST')}
                          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="GET">GET</option>
                          <option value="POST">POST</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Headers (JSON)</label>
                    <textarea
                      value={apiHeaders}
                      onChange={(e) => setApiHeaders(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      rows={2}
                      placeholder='{"Authorization": "Bearer your-api-key"}'
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Response Path</label>
                    <input
                      type="text"
                      value={apiResponsePath}
                      onChange={(e) => setApiResponsePath(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="data.securities (leave empty if response is array)"
                    />
                    <p className="text-xs text-muted-foreground mt-1">JSONPath to the securities array in API response</p>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => testAPIMutation.mutate()}
                    disabled={!apiEndpoint || testAPIMutation.isPending}
                  >
                    {testAPIMutation.isPending ? 'Testing...' : 'Test Connection'}
                  </Button>
                </>
              )}

              {/* Database Config */}
              {sourceType === 'database' && (
                <>
                  <div className="pt-4 border-t">
                    <h3 className="font-medium mb-3">Database Configuration</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Database Type</label>
                        <select
                          value={dbType}
                          onChange={(e) => setDbType(e.target.value as 'postgresql' | 'mysql')}
                          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="postgresql">PostgreSQL</option>
                          <option value="mysql">MySQL</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                        <input
                          type="number"
                          value={dbPort}
                          onChange={(e) => setDbPort(e.target.value)}
                          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          placeholder={dbType === 'postgresql' ? '5432' : '3306'}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Host *</label>
                      <input
                        type="text"
                        value={dbHost}
                        onChange={(e) => setDbHost(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="localhost or db.example.com"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Database Name *</label>
                      <input
                        type="text"
                        value={dbName}
                        onChange={(e) => setDbName(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="securities_db"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Username *</label>
                      <input
                        type="text"
                        value={dbUsername}
                        onChange={(e) => setDbUsername(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="db_user"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                      <input
                        type="password"
                        value={dbPassword}
                        onChange={(e) => setDbPassword(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="••••••••"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SQL Query *</label>
                    <textarea
                      value={dbQuery}
                      onChange={(e) => setDbQuery(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      rows={3}
                      placeholder="SELECT symbol, company_name, sector FROM my_securities"
                    />
                    <p className="text-xs text-muted-foreground mt-1">Query must return columns - you'll map them to our fields below</p>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => testDBMutation.mutate()}
                    disabled={!dbHost || !dbName || !dbUsername || testDBMutation.isPending}
                  >
                    {testDBMutation.isPending ? 'Testing...' : 'Test Connection'}
                  </Button>
                </>
              )}

              {/* Field Mapping for API/DB */}
              {(sourceType === 'api_endpoint' || sourceType === 'database') && (
                <div className="pt-4 border-t">
                  <h3 className="font-medium mb-1">Field Mapping</h3>
                  <p className="text-sm text-muted-foreground mb-3">
                    Map your source field names to our schema. Use the exact column/field names from your data.
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Ticker Field * <span className="text-muted-foreground font-normal">(your column name)</span>
                      </label>
                      <input
                        type="text"
                        value={tickerField}
                        onChange={(e) => setTickerField(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., symbol, ticker_id, stock_code"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Name Field <span className="text-muted-foreground font-normal">(optional)</span>
                      </label>
                      <input
                        type="text"
                        value={nameField}
                        onChange={(e) => setNameField(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., company_name, security_name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Sector Field <span className="text-muted-foreground font-normal">(optional)</span>
                      </label>
                      <input
                        type="text"
                        value={sectorField}
                        onChange={(e) => setSectorField(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., gics_sector, industry_group"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Market Cap Field <span className="text-muted-foreground font-normal">(optional)</span>
                      </label>
                      <input
                        type="text"
                        value={marketCapField}
                        onChange={(e) => setMarketCapField(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., mkt_cap, market_value"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Test Result */}
              {testResult && (
                <div className={`p-3 rounded-lg ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                  {testResult.success ? (
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4" />
                      <span>Connection successful!</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4" />
                      <span>{testResult.error}</span>
                    </div>
                  )}
                </div>
              )}

              {createMutation.isError && (
                <div className="bg-red-50 text-red-700 px-3 py-2 rounded-lg text-sm">
                  {(createMutation.error as any)?.response?.data?.detail || 'Failed to create'}
                </div>
              )}

              <div className="flex gap-3 pt-4 border-t">
                <Button variant="outline" onClick={() => step === 'config' ? setStep('type') : onClose()}>
                  {step === 'config' ? 'Back' : 'Cancel'}
                </Button>
                <Button
                  className="flex-1"
                  onClick={() => createMutation.mutate()}
                  disabled={!name || createMutation.isPending ||
                    (sourceType === 'api_endpoint' && !apiEndpoint) ||
                    (sourceType === 'database' && (!dbHost || !dbName || !dbUsername || !dbQuery))
                  }
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Data Source'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function AddSecuritiesDialog({
  dataSourceId,
  onClose,
}: {
  dataSourceId: string
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<'manual' | 'csv'>('manual')
  const [tickerList, setTickerList] = useState('')

  // CSV state
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [csvColumns, setCsvColumns] = useState<string[]>([])
  const [csvPreview, setCsvPreview] = useState<Record<string, string>[]>([])
  const [showColumnMapping, setShowColumnMapping] = useState(false)

  // Column mapping - user can pick any column from their CSV
  const [tickerColumn, setTickerColumn] = useState('')
  const [nameColumn, setNameColumn] = useState('')
  const [sectorColumn, setSectorColumn] = useState('')
  const [countryColumn, setCountryColumn] = useState('')
  const [marketCapColumn, setMarketCapColumn] = useState('')
  const [priceColumn, setPriceColumn] = useState('')

  const addSecuritiesMutation = useMutation({
    mutationFn: (securities: SecurityData[]) =>
      dataSourcesApi.addSecurities(dataSourceId, securities),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSource', dataSourceId] })
      queryClient.invalidateQueries({ queryKey: ['dataSources'] })
      onClose()
    },
  })

  const importCSVMutation = useMutation({
    mutationFn: ({ file, mapping }: { file: File; mapping: CSVColumnMapping }) =>
      dataSourcesApi.importCSV(dataSourceId, file, mapping),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSource', dataSourceId] })
      queryClient.invalidateQueries({ queryKey: ['dataSources'] })
      onClose()
    },
  })

  const handleManualAdd = () => {
    const tickers = tickerList
      .split(/[\n,;]+/)
      .map((t) => t.trim().toUpperCase())
      .filter((t) => t.length > 0)

    if (tickers.length === 0) return

    const securities: SecurityData[] = tickers.map((ticker) => ({ ticker }))
    addSecuritiesMutation.mutate(securities)
  }

  // Parse CSV to detect columns and show preview
  const handleFileSelect = async (file: File) => {
    setCsvFile(file)

    const text = await file.text()
    const lines = text.split('\n').filter(line => line.trim())

    if (lines.length === 0) return

    // Parse header
    const headers = lines[0].split(',').map(h => h.trim().replace(/^["']|["']$/g, ''))
    setCsvColumns(headers)

    // Parse first few rows for preview
    const preview: Record<string, string>[] = []
    for (let i = 1; i < Math.min(4, lines.length); i++) {
      const values = lines[i].split(',').map(v => v.trim().replace(/^["']|["']$/g, ''))
      const row: Record<string, string> = {}
      headers.forEach((header, idx) => {
        row[header] = values[idx] || ''
      })
      preview.push(row)
    }
    setCsvPreview(preview)

    // Auto-detect common column names
    const lowerHeaders = headers.map(h => h.toLowerCase())

    // Try to auto-map columns
    const tickerAliases = ['ticker', 'symbol', 'stock', 'code', 'stock_code', 'ticker_symbol']
    const nameAliases = ['name', 'company', 'company_name', 'security_name', 'description']
    const sectorAliases = ['sector', 'gics_sector', 'industry_sector', 'segment']
    const countryAliases = ['country', 'country_code', 'region', 'market']
    const marketCapAliases = ['market_cap', 'marketcap', 'mkt_cap', 'market_value', 'capitalization']
    const priceAliases = ['price', 'close', 'last_price', 'current_price', 'close_price']

    const findMatch = (aliases: string[]) => {
      for (const alias of aliases) {
        const idx = lowerHeaders.findIndex(h => h === alias || h.includes(alias))
        if (idx !== -1) return headers[idx]
      }
      return ''
    }

    setTickerColumn(findMatch(tickerAliases) || headers[0]) // Default to first column
    setNameColumn(findMatch(nameAliases))
    setSectorColumn(findMatch(sectorAliases))
    setCountryColumn(findMatch(countryAliases))
    setMarketCapColumn(findMatch(marketCapAliases))
    setPriceColumn(findMatch(priceAliases))

    setShowColumnMapping(true)
  }

  const handleCSVUpload = () => {
    if (!csvFile || !tickerColumn) return

    const mapping: CSVColumnMapping = {
      ticker_column: tickerColumn,
      name_column: nameColumn || undefined,
      sector_column: sectorColumn || undefined,
      country_column: countryColumn || undefined,
      market_cap_column: marketCapColumn || undefined,
      price_column: priceColumn || undefined,
    }

    importCSVMutation.mutate({ file: csvFile, mapping })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto py-8">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Add Securities</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => { setMode('manual'); setShowColumnMapping(false); }}
              className={`flex-1 py-2 px-4 rounded-lg font-medium ${mode === 'manual'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              Manual Entry
            </button>
            <button
              onClick={() => setMode('csv')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium ${mode === 'csv'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              CSV Upload
            </button>
          </div>

          {mode === 'manual' ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ticker Symbols
                </label>
                <textarea
                  value={tickerList}
                  onChange={(e) => setTickerList(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono"
                  rows={6}
                  placeholder="AAPL&#10;MSFT&#10;GOOGL&#10;AMZN"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Enter one ticker per line, or separate with commas
                </p>
              </div>

              {addSecuritiesMutation.isError && (
                <div className="bg-red-50 text-red-700 px-3 py-2 rounded-lg text-sm">
                  {(addSecuritiesMutation.error as any)?.response?.data?.detail || 'Failed to add'}
                </div>
              )}

              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleManualAdd}
                  disabled={!tickerList.trim() || addSecuritiesMutation.isPending}
                >
                  {addSecuritiesMutation.isPending ? 'Adding...' : 'Add Securities'}
                </Button>
              </div>
            </div>
          ) : !showColumnMapping ? (
            <div className="space-y-4">
              <div
                className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleFileSelect(file)
                  }}
                />
                <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-2" />
                <p className="font-medium">Click to upload any CSV file</p>
                <p className="text-sm text-muted-foreground mt-1">
                  We'll auto-detect columns and let you map them
                </p>
              </div>

              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-blue-700">
                  <strong>Flexible CSV Import:</strong> Your CSV can have any column names.
                  After upload, you'll map your columns to our fields (ticker, name, sector, etc.).
                </p>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={onClose}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* File info */}
              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                <FileSpreadsheet className="h-5 w-5 text-green-600" />
                <div className="flex-1">
                  <p className="font-medium text-green-700">{csvFile?.name}</p>
                  <p className="text-sm text-green-600">{csvColumns.length} columns detected</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setCsvFile(null)
                    setCsvColumns([])
                    setCsvPreview([])
                    setShowColumnMapping(false)
                  }}
                >
                  Change
                </Button>
              </div>

              {/* Column Preview */}
              <div className="bg-muted/30 rounded-lg p-4 overflow-x-auto">
                <p className="text-sm font-medium mb-2">Preview (first 3 rows):</p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      {csvColumns.map(col => (
                        <th key={col} className="px-2 py-1 text-left font-mono text-xs bg-muted/50">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {csvPreview.map((row, idx) => (
                      <tr key={idx} className="border-b border-muted/50">
                        {csvColumns.map(col => (
                          <td key={col} className="px-2 py-1 truncate max-w-[150px]">
                            {row[col]}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Column Mapping */}
              <div className="border-t pt-4">
                <h3 className="font-medium mb-3">Map Your Columns</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Select which of your CSV columns map to each field. Only Ticker is required.
                </p>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Ticker Column * <span className="text-red-500">(required)</span>
                    </label>
                    <select
                      value={tickerColumn}
                      onChange={(e) => setTickerColumn(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">-- Select column --</option>
                      {csvColumns.map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name Column</label>
                    <select
                      value={nameColumn}
                      onChange={(e) => setNameColumn(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">-- None --</option>
                      {csvColumns.map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Sector Column</label>
                    <select
                      value={sectorColumn}
                      onChange={(e) => setSectorColumn(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">-- None --</option>
                      {csvColumns.map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Country Column</label>
                    <select
                      value={countryColumn}
                      onChange={(e) => setCountryColumn(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">-- None --</option>
                      {csvColumns.map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Market Cap Column</label>
                    <select
                      value={marketCapColumn}
                      onChange={(e) => setMarketCapColumn(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">-- None --</option>
                      {csvColumns.map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Price Column</label>
                    <select
                      value={priceColumn}
                      onChange={(e) => setPriceColumn(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">-- None --</option>
                      {csvColumns.map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {importCSVMutation.isError && (
                <div className="bg-red-50 text-red-700 px-3 py-2 rounded-lg text-sm">
                  {(importCSVMutation.error as any)?.response?.data?.detail || 'Failed to import'}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button variant="outline" onClick={() => setShowColumnMapping(false)}>
                  Back
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleCSVUpload}
                  disabled={!tickerColumn || importCSVMutation.isPending}
                >
                  {importCSVMutation.isPending ? 'Importing...' : 'Import CSV'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
