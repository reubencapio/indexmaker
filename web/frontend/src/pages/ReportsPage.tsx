import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  FileText, Download, Plus, Trash2, Clock, CheckCircle, 
  AlertCircle, Loader2, X, Eye
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { reportsApi, indicesApi, GenerateReportRequest } from '@/lib/api'
import { format } from 'date-fns'

export function ReportsPage() {
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const queryClient = useQueryClient()

  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: () => reportsApi.list(),
    refetchInterval: 5000, // Poll for status updates
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => reportsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reports'] }),
  })

  const downloadReport = async (id: string) => {
    try {
      const blob = await reportsApi.download(id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report-${id.slice(0, 8)}.html`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Download failed:', error)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="flex items-center gap-1 text-green-600 bg-green-50 px-2 py-1 rounded-full text-xs">
            <CheckCircle className="h-3 w-3" /> Completed
          </span>
        )
      case 'generating':
        return (
          <span className="flex items-center gap-1 text-blue-600 bg-blue-50 px-2 py-1 rounded-full text-xs">
            <Loader2 className="h-3 w-3 animate-spin" /> Generating
          </span>
        )
      case 'failed':
        return (
          <span className="flex items-center gap-1 text-red-600 bg-red-50 px-2 py-1 rounded-full text-xs">
            <AlertCircle className="h-3 w-3" /> Failed
          </span>
        )
      default:
        return (
          <span className="flex items-center gap-1 text-yellow-600 bg-yellow-50 px-2 py-1 rounded-full text-xs">
            <Clock className="h-3 w-3" /> Pending
          </span>
        )
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Reports & Factsheets</h1>
          <p className="text-muted-foreground">
            Generate professional reports and factsheets for your indices
          </p>
        </div>
        <Button onClick={() => setShowGenerateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Generate Report
        </Button>
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-3 gap-4">
        <QuickFactsheetCard />
      </div>

      {/* Reports List */}
      <div className="bg-card rounded-xl border">
        <div className="p-4 border-b">
          <h2 className="font-semibold">Generated Reports</h2>
        </div>
        
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Loading...</div>
        ) : !reports?.length ? (
          <div className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No reports yet</h3>
            <p className="text-muted-foreground mb-4">
              Generate your first report to get started
            </p>
            <Button onClick={() => setShowGenerateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Generate Report
            </Button>
          </div>
        ) : (
          <div className="divide-y">
            {reports.map((report: any) => (
              <div key={report.id} className="p-4 flex items-center justify-between hover:bg-muted/50">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                    <FileText className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium">
                      {report.report_type.charAt(0).toUpperCase() + report.report_type.slice(1)} Report
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {format(new Date(report.as_of_date), 'PPP')} • {report.report_format.toUpperCase()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {getStatusBadge(report.status)}
                  <span className="text-sm text-muted-foreground">
                    {report.download_count} downloads
                  </span>
                  <div className="flex gap-2">
                    {report.status === 'completed' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => downloadReport(report.id)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => deleteMutation.mutate(report.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showGenerateDialog && (
        <GenerateReportDialog onClose={() => setShowGenerateDialog(false)} />
      )}
    </div>
  )
}

function QuickFactsheetCard() {
  const [selectedIndex, setSelectedIndex] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)

  const { data: indices } = useQuery({
    queryKey: ['indices'],
    queryFn: () => indicesApi.list(),
  })

  const generateQuickFactsheet = async () => {
    if (!selectedIndex) return
    setIsGenerating(true)
    try {
      const blob = await reportsApi.quickFactsheet(selectedIndex, 'html')
      const url = window.URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch (error) {
      console.error('Generation failed:', error)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white">
      <h3 className="font-semibold text-lg mb-2">Quick Factsheet</h3>
      <p className="text-blue-100 text-sm mb-4">
        Generate an instant HTML factsheet for any index
      </p>
      <div className="space-y-3">
        <select
          value={selectedIndex}
          onChange={(e) => setSelectedIndex(e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-gray-800"
        >
          <option value="">Select an index...</option>
          {indices?.map((index: any) => (
            <option key={index.id} value={index.id}>{index.name}</option>
          ))}
        </select>
        <Button
          onClick={generateQuickFactsheet}
          disabled={!selectedIndex || isGenerating}
          className="w-full bg-white text-blue-600 hover:bg-blue-50"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Eye className="h-4 w-4 mr-2" />
              View Factsheet
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

function GenerateReportDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [indexId, setIndexId] = useState('')
  const [reportType, setReportType] = useState('factsheet')
  const [reportFormat, setReportFormat] = useState('pdf')

  const { data: indices } = useQuery({
    queryKey: ['indices'],
    queryFn: () => indicesApi.list(),
  })

  const generateMutation = useMutation({
    mutationFn: (data: GenerateReportRequest) => reportsApi.generate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Generate Report</h2>
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

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Report Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="factsheet">Factsheet</option>
                <option value="performance">Performance Report</option>
                <option value="components">Components Report</option>
                <option value="full">Full Report</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Format</label>
              <select
                value={reportFormat}
                onChange={(e) => setReportFormat(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="pdf">PDF</option>
                <option value="html">HTML</option>
                <option value="xlsx">Excel</option>
              </select>
            </div>
          </div>

          <div className="bg-blue-50 text-blue-700 p-4 rounded-lg text-sm">
            <strong>Note:</strong> Reports are generated asynchronously. 
            You'll be notified when your report is ready for download.
          </div>

          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1" onClick={onClose}>
              Cancel
            </Button>
            <Button
              className="flex-1"
              onClick={() => generateMutation.mutate({
                index_id: indexId,
                report_type: reportType,
                report_format: reportFormat as any,
              })}
              disabled={!indexId || generateMutation.isPending}
            >
              {generateMutation.isPending ? 'Starting...' : 'Generate Report'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

