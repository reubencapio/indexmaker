import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Webhook, Mail, Server, Plus, Trash2, TestTube, CheckCircle,
  AlertCircle, Clock, X, Send
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { deliveryApi, getErrorMessage, isUpgradeError, CreateWebhookRequest, CreateEmailSubscriptionRequest, CreateSFTPRequest } from '@/lib/api'
import { format } from 'date-fns'
import { toast } from 'sonner'

type TabType = 'webhooks' | 'email' | 'sftp'

export function DeliveryPage() {
  const [activeTab, setActiveTab] = useState<TabType>('webhooks')
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const tabs = [
    { id: 'webhooks', name: 'Webhooks', icon: Webhook, desc: 'Sent when an index is recalculated or rebalanced' },
    { id: 'email', name: 'Email Reports', icon: Mail, desc: 'A summary of your indices, emailed on a schedule' },
    { id: 'sftp', name: 'SFTP Delivery', icon: Server, desc: 'File transfer to servers' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Data Delivery</h1>
          <p className="text-muted-foreground">
            Configure how your index data is delivered
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add {activeTab === 'webhooks' ? 'Webhook' : activeTab === 'email' ? 'Email Report' : 'SFTP Destination'}
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as TabType)}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${activeTab === tab.id
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.name}
          </button>
        ))}
      </div>

      {activeTab === 'webhooks' ? (
        <p className="text-sm text-muted-foreground">
          A signed JSON payload is posted to your URL each time one of your indices is recalculated or
          rebalanced. Verify it with the <code className="font-mono">X-Webhook-Signature</code> header: an
          HMAC-SHA256 of the request body using your webhook's secret.
        </p>
      ) : activeTab === 'email' ? (
        <p className="text-sm text-muted-foreground">
          Each report lists your indices with their level, trailing returns and top holdings, and can attach a
          factsheet for each one. Reports go out at the time you choose, in UTC. Use "Send now" to see exactly
          what recipients will get.
        </p>
      ) : (
        // Destinations can be saved, but nothing uploads on a schedule yet. Saying
        // so is better than a customer waiting for a file that never arrives.
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Scheduled SFTP uploads aren't running yet. You can save destinations now and they will start once
          uploads are switched on. Webhooks and email reports are live today.
        </div>
      )}

      {/* Content */}
      {activeTab === 'webhooks' && <WebhooksTab />}
      {activeTab === 'email' && <EmailTab />}
      {activeTab === 'sftp' && <SFTPTab />}

      {/* Create Dialogs */}
      {showCreateDialog && activeTab === 'webhooks' && (
        <CreateWebhookDialog onClose={() => setShowCreateDialog(false)} />
      )}
      {showCreateDialog && activeTab === 'email' && (
        <CreateEmailDialog onClose={() => setShowCreateDialog(false)} />
      )}
      {showCreateDialog && activeTab === 'sftp' && (
        <CreateSFTPDialog onClose={() => setShowCreateDialog(false)} />
      )}
    </div>
  )
}

function WebhooksTab() {
  const queryClient = useQueryClient()
  const { data: webhooks, isLoading } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => deliveryApi.listWebhooks(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deliveryApi.deleteWebhook(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['webhooks'] }),
  })

  const testMutation = useMutation({
    mutationFn: (id: string) => deliveryApi.testWebhook(id),
  })

  if (isLoading) return <div className="text-center py-8">Loading...</div>

  if (!webhooks?.length) {
    return (
      <div className="bg-card rounded-xl border p-12 text-center">
        <Webhook className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">No webhooks configured</h3>
        <p className="text-muted-foreground mb-4">
          Add a webhook to receive real-time notifications when your indices update
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {webhooks.map((webhook: any) => (
        <div key={webhook.id} className="bg-card rounded-xl border p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${webhook.is_active ? 'bg-green-100' : 'bg-gray-100'
                }`}>
                <Webhook className={`h-5 w-5 ${webhook.is_active ? 'text-green-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <h3 className="font-semibold">{webhook.name}</h3>
                <p className="text-sm text-muted-foreground font-mono">{webhook.url}</p>
                <div className="flex items-center gap-4 mt-2 text-sm">
                  <span className="flex items-center gap-1">
                    <Send className="h-3 w-3" />
                    {webhook.total_deliveries} sent
                  </span>
                  <span className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-green-500" />
                    {webhook.successful_deliveries} success
                  </span>
                  {webhook.last_error && (
                    <span className="flex items-center gap-1 text-red-500">
                      <AlertCircle className="h-3 w-3" />
                      {webhook.last_error}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => testMutation.mutate(webhook.id)}
                disabled={testMutation.isPending}
              >
                <TestTube className="h-4 w-4 mr-1" />
                {testMutation.isPending ? 'Testing...' : 'Test'}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => deleteMutation.mutate(webhook.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          {testMutation.data && testMutation.variables === webhook.id && (
            <div className={`mt-4 p-3 rounded-lg text-sm ${testMutation.data.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
              {testMutation.data.success
                ? `✓ Test successful (HTTP ${testMutation.data.status_code})`
                : `✗ Test failed: ${testMutation.data.error}`
              }
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function describeSchedule(sub: { frequency: string; schedule_time: string | null; schedule_day: number | null }) {
  const time = `${sub.schedule_time || '08:00'} UTC`
  if (sub.frequency === 'weekly') return `Every ${WEEKDAYS[sub.schedule_day ?? 0] ?? 'Monday'} at ${time}`
  if (sub.frequency === 'monthly') return `Day ${sub.schedule_day || 1} of each month at ${time}`
  return `Every day at ${time}`
}

function EmailTab() {
  const queryClient = useQueryClient()
  const { data: subscriptions, isLoading } = useQuery({
    queryKey: ['emailSubscriptions'],
    queryFn: () => deliveryApi.listEmail(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deliveryApi.deleteEmail(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['emailSubscriptions'] }),
  })

  const sendNowMutation = useMutation({
    mutationFn: (id: string) => deliveryApi.sendEmailNow(id),
    onSuccess: () => toast.success('Report sent'),
    onError: (error) => {
      if (!isUpgradeError(error)) toast.error(getErrorMessage(error, 'The report could not be sent.'))
    },
    // Success and failure both change last sent / last error on the row.
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['emailSubscriptions'] }),
  })

  if (isLoading) return <div className="text-center py-8">Loading...</div>

  if (!subscriptions?.length) {
    return (
      <div className="bg-card rounded-xl border p-12 text-center">
        <Mail className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">No email reports yet</h3>
        <p className="text-muted-foreground mb-4">
          Add one to get a summary of your indices in your inbox every day, week or month.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {subscriptions.map((sub: any) => (
        <div key={sub.id} className="bg-card rounded-xl border p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${sub.is_active ? 'bg-blue-100' : 'bg-gray-100'
                }`}>
                <Mail className={`h-5 w-5 ${sub.is_active ? 'text-blue-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <h3 className="font-semibold">{sub.name}</h3>
                <p className="text-sm text-muted-foreground">
                  {sub.recipients?.join(', ')}
                </p>
                <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {describeSchedule(sub)}
                  </span>
                  <span>
                    {sub.last_sent_at ? `Last sent: ${format(new Date(sub.last_sent_at), 'PPp')}` : 'Not sent yet'}
                  </span>
                </div>
                {sub.last_error && (
                  <p className="mt-2 flex items-start gap-1.5 text-sm text-red-600">
                    <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    {sub.last_error}
                  </p>
                )}
              </div>
            </div>
            <div className="flex flex-shrink-0 gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => sendNowMutation.mutate(sub.id)}
                disabled={sendNowMutation.isPending}
              >
                <Send className="h-4 w-4 mr-2" />
                {sendNowMutation.isPending && sendNowMutation.variables === sub.id ? 'Sending...' : 'Send now'}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                aria-label={`Delete ${sub.name}`}
                onClick={() => deleteMutation.mutate(sub.id)}
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

function SFTPTab() {
  const queryClient = useQueryClient()
  const { data: destinations, isLoading } = useQuery({
    queryKey: ['sftpDestinations'],
    queryFn: () => deliveryApi.listSFTP(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deliveryApi.deleteSFTP(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sftpDestinations'] }),
  })

  const testMutation = useMutation({
    mutationFn: (id: string) => deliveryApi.testSFTP(id),
  })

  if (isLoading) return <div className="text-center py-8">Loading...</div>

  if (!destinations?.length) {
    return (
      <div className="bg-card rounded-xl border p-12 text-center">
        <Server className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">No SFTP destinations</h3>
        <p className="text-muted-foreground mb-4">
          Configure SFTP to automatically deliver index data files
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {destinations.map((dest: any) => (
        <div key={dest.id} className="bg-card rounded-xl border p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${dest.is_active ? 'bg-purple-100' : 'bg-gray-100'
                }`}>
                <Server className={`h-5 w-5 ${dest.is_active ? 'text-purple-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <h3 className="font-semibold">{dest.name}</h3>
                <p className="text-sm text-muted-foreground font-mono">
                  {dest.username}@{dest.host}:{dest.port}{dest.remote_path}
                </p>
                <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                  <span>{dest.frequency}</span>
                  <span>Format: {dest.file_format?.toUpperCase()}</span>
                  {dest.last_success_at && (
                    <span>Last: {format(new Date(dest.last_success_at), 'PPp')}</span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => testMutation.mutate(dest.id)}
                disabled={testMutation.isPending}
              >
                <TestTube className="h-4 w-4 mr-1" />
                Test
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => deleteMutation.mutate(dest.id)}
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

function CreateWebhookDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [events, setEvents] = useState(['index_update', 'rebalance'])

  const createMutation = useMutation({
    mutationFn: (data: CreateWebhookRequest) => deliveryApi.createWebhook(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Add Webhook</h2>
          <button onClick={onClose}><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="My Webhook"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">URL</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
              placeholder="https://your-server.com/webhook"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Events</label>
            <div className="space-y-2">
              {['index_update', 'rebalance', 'corporate_action'].map((event) => (
                <label key={event} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={events.includes(event)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setEvents([...events, event])
                      } else {
                        setEvents(events.filter((e) => e !== event))
                      }
                    }}
                    className="rounded"
                  />
                  <span className="capitalize">{event.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1" onClick={onClose}>
              Cancel
            </Button>
            <Button
              className="flex-1"
              onClick={() => createMutation.mutate({ name, url, events })}
              disabled={!name || !url || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create Webhook'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function CreateEmailDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [recipients, setRecipients] = useState('')
  const [frequency, setFrequency] = useState<'daily' | 'weekly' | 'monthly'>('weekly')
  const [time, setTime] = useState('08:00')
  const [weekday, setWeekday] = useState(0)
  const [monthDay, setMonthDay] = useState(1)
  const [reportType, setReportType] = useState('factsheet')
  const [attach, setAttach] = useState(true)

  const createMutation = useMutation({
    mutationFn: (data: CreateEmailSubscriptionRequest) => deliveryApi.createEmail(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailSubscriptions'] })
      toast.success('Email report scheduled')
      onClose()
    },
  })

  const addresses = recipients.split(',').map((r) => r.trim()).filter(Boolean)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Schedule an email report</h2>
          <button onClick={onClose} aria-label="Close"><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="report-name" className="block text-sm font-medium mb-1">Name</label>
            <input
              id="report-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="Weekly summary"
            />
          </div>
          <div>
            <label htmlFor="report-recipients" className="block text-sm font-medium mb-1">
              Recipients (comma-separated, up to 10)
            </label>
            <input
              id="report-recipients"
              type="text"
              value={recipients}
              onChange={(e) => setRecipients(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="you@example.com, client@example.com"
            />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label htmlFor="report-frequency" className="block text-sm font-medium mb-1">Frequency</label>
              <select
                id="report-frequency"
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as typeof frequency)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            {frequency === 'weekly' && (
              <div>
                <label htmlFor="report-weekday" className="block text-sm font-medium mb-1">Day</label>
                <select
                  id="report-weekday"
                  value={weekday}
                  onChange={(e) => setWeekday(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  {WEEKDAYS.map((day, i) => (
                    <option key={day} value={i}>{day}</option>
                  ))}
                </select>
              </div>
            )}
            {frequency === 'monthly' && (
              <div>
                <label htmlFor="report-monthday" className="block text-sm font-medium mb-1">Day of month</label>
                <select
                  id="report-monthday"
                  value={monthDay}
                  onChange={(e) => setMonthDay(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  {Array.from({ length: 28 }, (_, i) => i + 1).map((day) => (
                    <option key={day} value={day}>{day}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label htmlFor="report-time" className="block text-sm font-medium mb-1">Time (UTC)</label>
              <input
                id="report-time"
                type="time"
                step={3600}
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </div>
          <div>
            <label htmlFor="report-type" className="block text-sm font-medium mb-1">Contents</label>
            <select
              id="report-type"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="factsheet">Returns and top holdings</option>
              <option value="performance">Returns only</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={attach} onChange={(e) => setAttach(e.target.checked)} />
            Attach a factsheet for each index (first 5)
          </label>

          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button
              className="flex-1"
              onClick={() => createMutation.mutate({
                name,
                recipients: addresses,
                frequency,
                schedule_time: time.slice(0, 5) || '08:00',
                schedule_day: frequency === 'weekly' ? weekday : frequency === 'monthly' ? monthDay : undefined,
                report_type: reportType,
                include_attachments: attach,
              })}
              disabled={!name || addresses.length === 0 || addresses.length > 10 || createMutation.isPending}
            >
              {createMutation.isPending ? 'Saving...' : 'Schedule report'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function CreateSFTPDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [host, setHost] = useState('')
  const [port, setPort] = useState('22')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remotePath, setRemotePath] = useState('/')
  const [frequency, setFrequency] = useState('daily')
  const [fileFormat, setFileFormat] = useState('csv')

  const createMutation = useMutation({
    mutationFn: (data: CreateSFTPRequest) => deliveryApi.createSFTP(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sftpDestinations'] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto py-8">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Add SFTP Destination</h2>
          <button onClick={onClose}><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="Production Server"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">Host</label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="sftp.example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Port</label>
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Remote Path</label>
            <input
              type="text"
              value={remotePath}
              onChange={(e) => setRemotePath(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg font-mono"
              placeholder="/data/indices/"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Frequency</label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">File Format</label>
              <select
                value={fileFormat}
                onChange={(e) => setFileFormat(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
                <option value="xlsx">Excel</option>
              </select>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button
              className="flex-1"
              onClick={() => createMutation.mutate({
                name, host, port: parseInt(port), username, password,
                remote_path: remotePath, frequency, file_format: fileFormat,
              })}
              disabled={!name || !host || !username || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create Destination'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
