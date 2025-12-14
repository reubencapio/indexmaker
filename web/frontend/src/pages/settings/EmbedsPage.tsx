import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Link2, Code, Plus, Trash2, Copy, ExternalLink, Eye, 
  Lock, Globe, X, CheckCircle, BarChart3
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { embedsApi, indicesApi, CreatePublicShareRequest, CreateEmbedWidgetRequest } from '@/lib/api'
import { format } from 'date-fns'

type TabType = 'shares' | 'widgets'

export function EmbedsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('shares')
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Embeds & Shares</h1>
          <p className="text-muted-foreground">
            Share your indices publicly or embed them in your website
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          {activeTab === 'shares' ? 'Create Share Link' : 'Create Widget'}
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('shares')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
            activeTab === 'shares'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Link2 className="h-4 w-4" />
          Public Share Links
        </button>
        <button
          onClick={() => setActiveTab('widgets')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
            activeTab === 'widgets'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Code className="h-4 w-4" />
          Embed Widgets
        </button>
      </div>

      {/* Content */}
      {activeTab === 'shares' && <SharesTab />}
      {activeTab === 'widgets' && <WidgetsTab />}

      {/* Create Dialogs */}
      {showCreateDialog && activeTab === 'shares' && (
        <CreateShareDialog onClose={() => setShowCreateDialog(false)} />
      )}
      {showCreateDialog && activeTab === 'widgets' && (
        <CreateWidgetDialog onClose={() => setShowCreateDialog(false)} />
      )}
    </div>
  )
}

function SharesTab() {
  const queryClient = useQueryClient()
  const [copiedId, setCopiedId] = useState<string | null>(null)
  
  const { data: shares, isLoading } = useQuery({
    queryKey: ['publicShares'],
    queryFn: () => embedsApi.listShares(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => embedsApi.deleteShare(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['publicShares'] }),
  })

  const copyToClipboard = (url: string, id: string) => {
    navigator.clipboard.writeText(url)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  if (isLoading) return <div className="text-center py-8">Loading...</div>

  if (!shares?.length) {
    return (
      <div className="bg-card rounded-xl border p-12 text-center">
        <Link2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">No public share links</h3>
        <p className="text-muted-foreground mb-4">
          Create a share link to let anyone view your index without logging in
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {shares.map((share: any) => (
        <div key={share.id} className="bg-card rounded-xl border p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                share.is_active ? 'bg-green-100' : 'bg-gray-100'
              }`}>
                {share.has_password ? (
                  <Lock className={`h-5 w-5 ${share.is_active ? 'text-green-600' : 'text-gray-400'}`} />
                ) : (
                  <Globe className={`h-5 w-5 ${share.is_active ? 'text-green-600' : 'text-gray-400'}`} />
                )}
              </div>
              <div>
                <h3 className="font-semibold">{share.title_override || `Share: ${share.slug}`}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <code className="text-sm bg-muted px-2 py-1 rounded">
                    /public/{share.slug}
                  </code>
                  <button
                    onClick={() => copyToClipboard(share.public_url || `/public/${share.slug}`, share.id)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    {copiedId === share.id ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Eye className="h-3 w-3" />
                    {share.view_count} views
                  </span>
                  {share.has_password && <span>Password protected</span>}
                  {share.expires_at && (
                    <span>Expires: {format(new Date(share.expires_at), 'PP')}</span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(`/public/${share.slug}`, '_blank')}
              >
                <ExternalLink className="h-4 w-4" />
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => deleteMutation.mutate(share.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function WidgetsTab() {
  const queryClient = useQueryClient()
  const [copiedId, setCopiedId] = useState<string | null>(null)
  
  const { data: widgets, isLoading } = useQuery({
    queryKey: ['embedWidgets'],
    queryFn: () => embedsApi.listWidgets(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => embedsApi.deleteWidget(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['embedWidgets'] }),
  })

  const copyToClipboard = (code: string, id: string) => {
    navigator.clipboard.writeText(code)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  if (isLoading) return <div className="text-center py-8">Loading...</div>

  if (!widgets?.length) {
    return (
      <div className="bg-card rounded-xl border p-12 text-center">
        <Code className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">No embed widgets</h3>
        <p className="text-muted-foreground mb-4">
          Create an embed widget to display your index on external websites
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {widgets.map((widget: any) => (
        <div key={widget.id} className="bg-card rounded-xl border p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                widget.is_active ? 'bg-blue-100' : 'bg-gray-100'
              }`}>
                <BarChart3 className={`h-5 w-5 ${widget.is_active ? 'text-blue-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <h3 className="font-semibold">{widget.name}</h3>
                <p className="text-sm text-muted-foreground">
                  {widget.widget_type} • {widget.width} × {widget.height} • {widget.theme} theme
                </p>
                <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                  <span>Embeds: {widget.embed_count}</span>
                  {widget.chart_type && <span>Chart: {widget.chart_type}</span>}
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(widget.embed_code || '', widget.id)}
              >
                {copiedId === widget.id ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
                <span className="ml-1">Copy Code</span>
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => deleteMutation.mutate(widget.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          {/* Embed Code Preview */}
          <div className="mt-4 p-3 bg-muted rounded-lg">
            <p className="text-xs text-muted-foreground mb-1">Embed Code:</p>
            <code className="text-xs break-all">{widget.embed_code}</code>
          </div>
        </div>
      ))}
    </div>
  )
}

function CreateShareDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [indexId, setIndexId] = useState('')
  const [slug, setSlug] = useState('')
  const [password, setPassword] = useState('')
  const [showChart, setShowChart] = useState(true)
  const [showComponents, setShowComponents] = useState(true)
  const [showPerformance, setShowPerformance] = useState(true)

  const { data: indices } = useQuery({
    queryKey: ['indices'],
    queryFn: () => indicesApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: (data: CreatePublicShareRequest) => embedsApi.createShare(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['publicShares'] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Create Share Link</h2>
          <button onClick={onClose}><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Select Index</label>
            <select
              value={indexId}
              onChange={(e) => setIndexId(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="">Choose an index...</option>
              {indices?.map((index: any) => (
                <option key={index.id} value={index.id}>{index.name}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Custom Slug (optional)</label>
            <div className="flex items-center">
              <span className="text-muted-foreground">/public/</span>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                className="flex-1 px-3 py-2 border rounded-lg ml-1"
                placeholder="my-index"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Password (optional)</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="Leave empty for public access"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Show Sections</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={showChart} onChange={(e) => setShowChart(e.target.checked)} className="rounded" />
                Performance Chart
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={showComponents} onChange={(e) => setShowComponents(e.target.checked)} className="rounded" />
                Components List
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={showPerformance} onChange={(e) => setShowPerformance(e.target.checked)} className="rounded" />
                Performance Metrics
              </label>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button
              className="flex-1"
              onClick={() => createMutation.mutate({
                index_id: indexId,
                slug: slug || undefined,
                password: password || undefined,
                show_chart: showChart,
                show_components: showComponents,
                show_performance: showPerformance,
              })}
              disabled={!indexId || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create Share Link'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function CreateWidgetDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [indexId, setIndexId] = useState('')
  const [name, setName] = useState('')
  const [widgetType, setWidgetType] = useState('chart')
  const [theme, setTheme] = useState('light')
  const [chartType, setChartType] = useState('line')
  const [height, setHeight] = useState('400px')

  const { data: indices } = useQuery({
    queryKey: ['indices'],
    queryFn: () => indicesApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: (data: CreateEmbedWidgetRequest) => embedsApi.createWidget(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['embedWidgets'] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Create Embed Widget</h2>
          <button onClick={onClose}><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Select Index</label>
            <select
              value={indexId}
              onChange={(e) => setIndexId(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="">Choose an index...</option>
              {indices?.map((index: any) => (
                <option key={index.id} value={index.id}>{index.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Widget Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="My Chart Widget"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Widget Type</label>
              <select
                value={widgetType}
                onChange={(e) => setWidgetType(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="chart">Chart</option>
                <option value="table">Data Table</option>
                <option value="performance">Performance Card</option>
                <option value="components">Components List</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Theme</label>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto</option>
              </select>
            </div>
          </div>

          {widgetType === 'chart' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Chart Type</label>
                <select
                  value={chartType}
                  onChange={(e) => setChartType(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="line">Line</option>
                  <option value="area">Area</option>
                  <option value="candlestick">Candlestick</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Height</label>
                <input
                  type="text"
                  value={height}
                  onChange={(e) => setHeight(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="400px"
                />
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button
              className="flex-1"
              onClick={() => createMutation.mutate({
                index_id: indexId,
                name,
                widget_type: widgetType as any,
                theme: theme as any,
                chart_type: chartType as any,
                height,
              })}
              disabled={!indexId || !name || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create Widget'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

