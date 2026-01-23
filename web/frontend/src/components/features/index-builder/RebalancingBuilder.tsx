import { RebalancingConfig } from '../../../types'

interface RebalancingBuilderProps {
  config: RebalancingConfig
  onChange: (config: RebalancingConfig) => void
}

const FREQUENCIES = [
  { id: 'daily', name: 'Daily', icon: '📅', description: 'Rebalance every trading day' },
  { id: 'weekly', name: 'Weekly', icon: '📆', description: 'Rebalance once per week' },
  { id: 'monthly', name: 'Monthly', icon: '🗓️', description: 'Rebalance once per month' },
  { id: 'quarterly', name: 'Quarterly', icon: '📊', description: 'Rebalance every 3 months (Mar, Jun, Sep, Dec)' },
  { id: 'semi_annual', name: 'Semi-Annual', icon: '📈', description: 'Rebalance twice per year (Jun, Dec)' },
  { id: 'annual', name: 'Annual', icon: '📉', description: 'Rebalance once per year' },
]

export function RebalancingBuilder({ config, onChange }: RebalancingBuilderProps) {
  const updateConfig = (updates: Partial<RebalancingConfig>) => {
    onChange({ ...config, ...updates })
  }

  const selectedFrequency = FREQUENCIES.find(f => f.id === config.frequency)

  // Calculate next rebalancing dates based on frequency
  const getNextRebalanceDates = (): string[] => {
    const dates: Date[] = []
    const now = new Date()

    for (let i = 0; i < 4; i++) {
      const date = new Date(now)
      switch (config.frequency) {
        case 'daily':
          date.setDate(date.getDate() + i)
          break
        case 'weekly':
          date.setDate(date.getDate() + (i * 7))
          break
        case 'monthly':
          date.setMonth(date.getMonth() + i)
          break
        case 'quarterly':
          const quarterMonth = Math.floor(date.getMonth() / 3) * 3 + 2 // Mar, Jun, Sep, Dec
          date.setMonth(quarterMonth + (i * 3))
          date.setDate(15) // Mid-month
          break
        case 'semi_annual':
          const halfYear = date.getMonth() < 6 ? 5 : 11 // Jun or Dec
          date.setMonth(halfYear + (i * 6))
          date.setDate(15)
          break
        case 'annual':
          date.setMonth(11) // December
          date.setFullYear(date.getFullYear() + i)
          date.setDate(15)
          break
      }
      dates.push(date)
    }

    return dates.map(d => d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }))
  }

  return (
    <div className="space-y-8">
      {/* Frequency Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Rebalancing Frequency
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {FREQUENCIES.map(freq => (
            <button
              key={freq.id}
              onClick={() => updateConfig({ frequency: freq.id as RebalancingConfig['frequency'] })}
              className={`p-4 rounded-xl border-2 text-center transition-all ${config.frequency === freq.id
                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                : 'border-gray-200 hover:border-gray-300'
                }`}
            >
              <span className="text-2xl block mb-1">{freq.icon}</span>
              <span className="font-medium text-gray-900 text-sm">{freq.name}</span>
            </button>
          ))}
        </div>
        {selectedFrequency && (
          <p className="text-sm text-gray-500 mt-3">{selectedFrequency.description}</p>
        )}
      </div>

      {/* Rebalancing Schedule Preview */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Upcoming Rebalance Dates</h3>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {getNextRebalanceDates().map((date, i) => (
            <div
              key={i}
              className={`flex-shrink-0 px-4 py-3 rounded-lg border ${i === 0 ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-200'
                }`}
            >
              <div className="text-sm text-gray-500">
                {i === 0 ? 'Next' : `+${i}`}
              </div>
              <div className="font-medium text-gray-900">{date}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Advanced Settings</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Announcement Lead Days */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Announcement Lead Days
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="30"
                value={config.announcementLead || ''}
                onChange={(e) => updateConfig({
                  announcementLead: e.target.value ? Number(e.target.value) : undefined
                })}
                placeholder="0"
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg"
              />
              <span className="text-gray-500">business days</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              How many days before effective date to announce changes
            </p>
          </div>

          {/* Reference Date Offset */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Reference Date Offset
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="30"
                value={config.referenceDateOffset || ''}
                onChange={(e) => updateConfig({
                  referenceDateOffset: e.target.value ? Number(e.target.value) : undefined
                })}
                placeholder="0"
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg"
              />
              <span className="text-gray-500">business days</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Days before effective date to determine constituent data
            </p>
          </div>
        </div>
      </div>

      {/* Rebalancing Timeline */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Rebalancing Timeline</h3>

        <div className="relative mt-8 mb-8">
          {/* Timeline bar */}
          <div className="absolute left-0 right-0 top-1/2 h-1 bg-gray-200 -translate-y-1/2 rounded-full" />

          {/* Timeline events */}
          <div className="relative flex justify-between w-full">
            {[
              {
                key: 'announcement',
                name: 'Announcement',
                offset: config.announcementLead || 0,
                color: 'bg-blue-500',
                visible: !!config.announcementLead
              },
              {
                key: 'reference',
                name: 'Reference Date',
                offset: config.referenceDateOffset || 0,
                color: 'bg-amber-500', // Changed to amber for better visibility
                visible: !!config.referenceDateOffset
              },
              {
                key: 'effective',
                name: 'Effective Date',
                offset: 0,
                color: 'bg-green-500',
                visible: true
              }
            ]
              .filter(e => e.visible)
              .sort((a, b) => b.offset - a.offset) // Sort descending (largest offset = earliest date)
              .map((event) => {
                // Calculate relative positioning if we wanted exact scale, but justify-between is cleaner for abstract view
                // We'll stick to justify-between which provides equal spacing, which is standard for process flows
                return (
                  <div key={event.key} className="flex flex-col items-center z-10">
                    {/* Dot */}
                    <div className={`w-5 h-5 rounded-full ${event.color} ring-4 ring-white shadow-sm flex items-center justify-center`} />

                    {/* Label */}
                    <div className="absolute top-8 w-32 text-center flex flex-col items-center">
                      <span className="text-sm font-semibold text-gray-900">{event.name}</span>
                      <span className="text-xs text-gray-500 font-mono mt-1">
                        {event.offset === 0 ? 'T' : `T - ${event.offset}d`}
                      </span>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>

        {/* Spacing for labels */}
        <div className="h-12" />

        <div className="mt-6 bg-blue-50 rounded-lg p-4 text-sm text-blue-800">
          <strong>How it works:</strong>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            <li>
              Data is captured on the <strong>Reference Date</strong>
              {config.referenceDateOffset ? ` (${config.referenceDateOffset} days before effective)` : ' (same as effective date)'}
            </li>
            <li>
              Changes are announced
              {config.announcementLead ? ` ${config.announcementLead} business days before effective date` : ' on the effective date'}
            </li>
            <li>
              New weights become effective on the <strong>Effective Date</strong>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
