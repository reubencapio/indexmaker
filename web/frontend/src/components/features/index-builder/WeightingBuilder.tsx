import { WeightingConfig, FACTORS } from '../../../types'

interface WeightingBuilderProps {
  config: WeightingConfig
  onChange: (config: WeightingConfig) => void
}

const WEIGHTING_METHODS = [
  {
    id: 'equal',
    name: 'Equal Weight',
    icon: '⚖️',
    description: 'Each constituent receives the same weight',
    formula: 'Weight = 1 / N',
  },
  {
    id: 'market_cap',
    name: 'Market Cap Weighted',
    icon: '📊',
    description: 'Weight proportional to market capitalization',
    formula: 'Weight = MCap_i / Σ MCap',
  },
  {
    id: 'free_float_market_cap',
    name: 'Free Float Market Cap',
    icon: '📈',
    description: 'Weight proportional to free float adjusted market cap',
    formula: 'Weight = (MCap × FF)_i / Σ(MCap × FF)',
  },
  {
    id: 'factor',
    name: 'Factor Weighted',
    icon: '🎯',
    description: 'Weight based on a specific factor',
    formula: 'Weight = Factor_i / Σ Factor',
  },
  {
    id: 'custom',
    name: 'Custom Weights',
    icon: '✏️',
    description: 'Manually define weights for each constituent',
    formula: 'User-defined',
  },
]

export function WeightingBuilder({ config, onChange }: WeightingBuilderProps) {
  const updateConfig = (updates: Partial<WeightingConfig>) => {
    onChange({ ...config, ...updates })
  }

  const selectedMethod = WEIGHTING_METHODS.find(m => m.id === config.method)

  return (
    <div className="space-y-8">
      {/* Weighting Method Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Weighting Method
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {WEIGHTING_METHODS.map(method => (
            <button
              key={method.id}
              onClick={() => updateConfig({ method: method.id as WeightingConfig['method'] })}
              className={`p-5 rounded-xl border-2 text-left transition-all ${
                config.method === method.id
                  ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{method.icon}</span>
                <span className="font-semibold text-gray-900">{method.name}</span>
              </div>
              <p className="text-sm text-gray-600 mb-2">{method.description}</p>
              <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-700">
                {method.formula}
              </code>
            </button>
          ))}
        </div>
      </div>

      {/* Factor Selection (for factor-weighted) */}
      {config.method === 'factor' && (
        <div className="bg-gray-50 rounded-xl p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Factor for Weighting</h3>
          <select
            value={config.factorField || ''}
            onChange={(e) => updateConfig({ factorField: e.target.value })}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a factor...</option>
            {FACTORS.map(factor => (
              <option key={factor.id} value={factor.field}>
                {factor.name} ({factor.category})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Weight Constraints */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Weight Constraints</h3>
        <p className="text-sm text-gray-500 mb-4">
          Set limits on individual constituent weights to ensure diversification
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Maximum Weight per Constituent
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={config.maxWeight ? config.maxWeight * 100 : ''}
                onChange={(e) => updateConfig({ 
                  maxWeight: e.target.value ? Number(e.target.value) / 100 : undefined 
                })}
                placeholder="No limit"
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg"
              />
              <span className="text-gray-500">%</span>
              <div className="flex gap-2 ml-4">
                {[5, 10, 15, 20, 25].map(pct => (
                  <button
                    key={pct}
                    onClick={() => updateConfig({ maxWeight: pct / 100 })}
                    className={`px-3 py-1 rounded text-sm transition-colors ${
                      config.maxWeight === pct / 100
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                    }`}
                  >
                    {pct}%
                  </button>
                ))}
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Weights exceeding this cap will be redistributed proportionally
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Minimum Weight per Constituent
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={config.minWeight ? config.minWeight * 100 : ''}
                onChange={(e) => updateConfig({ 
                  minWeight: e.target.value ? Number(e.target.value) / 100 : undefined 
                })}
                placeholder="No minimum"
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg"
              />
              <span className="text-gray-500">%</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Securities below this weight may be excluded (optional)
            </p>
          </div>
        </div>
      </div>

      {/* Visual Weight Distribution Preview */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Weight Distribution Preview</h3>
        <div className="space-y-4">
          {/* Example visualization */}
          <div className="relative h-8 bg-gray-100 rounded-lg overflow-hidden">
            {config.method === 'equal' ? (
              // Equal weight bars
              <div className="flex h-full">
                {[...Array(10)].map((_, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-blue-500 border-r border-white"
                    style={{ opacity: 1 - i * 0.05 }}
                  />
                ))}
              </div>
            ) : (
              // Market cap style distribution
              <div className="flex h-full">
                <div className="bg-blue-600" style={{ width: config.maxWeight ? `${config.maxWeight * 100}%` : '25%' }} />
                <div className="bg-blue-500" style={{ width: '15%' }} />
                <div className="bg-blue-400" style={{ width: '12%' }} />
                <div className="bg-blue-300" style={{ width: '10%' }} />
                <div className="bg-blue-200 flex-1" />
              </div>
            )}
          </div>
          
          <div className="flex justify-between text-sm text-gray-500">
            <span>Largest constituent</span>
            <span>Smallest constituents</span>
          </div>

          {/* Method-specific notes */}
          {selectedMethod && (
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl">{selectedMethod.icon}</span>
                <div>
                  <h4 className="font-medium text-blue-900">{selectedMethod.name}</h4>
                  <p className="text-sm text-blue-800 mt-1">{selectedMethod.description}</p>
                  {config.maxWeight && (
                    <p className="text-sm text-blue-700 mt-2">
                      Maximum weight capped at <strong>{(config.maxWeight * 100).toFixed(1)}%</strong>
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}



