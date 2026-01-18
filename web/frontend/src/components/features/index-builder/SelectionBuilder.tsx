import { useState } from 'react'
import { SelectionConfig, FactorConfig, ScoreRange, FACTORS } from '../../../types'

interface SelectionBuilderProps {
  config: SelectionConfig
  onChange: (config: SelectionConfig) => void
}

export function SelectionBuilder({ config, onChange }: SelectionBuilderProps) {
  const [showFactorModal, setShowFactorModal] = useState(false)

  const updateConfig = (updates: Partial<SelectionConfig>) => {
    onChange({ ...config, ...updates })
  }

  const addFactor = (factor: typeof FACTORS[number]) => {
    const newFactor: FactorConfig = {
      id: `${factor.id}-${Date.now()}`,
      name: factor.name,
      field: factor.field,
      weight: 100 / (config.factors.length + 1),
      direction: 'desc',
    }

    // Redistribute weights
    const newFactors = [...config.factors, newFactor].map(f => ({
      ...f,
      weight: 100 / (config.factors.length + 1)
    }))

    updateConfig({ factors: newFactors })
    setShowFactorModal(false)
  }

  const removeFactor = (id: string) => {
    const newFactors = config.factors.filter(f => f.id !== id)
    // Redistribute weights
    const redistributed = newFactors.map(f => ({
      ...f,
      weight: newFactors.length > 0 ? 100 / newFactors.length : 100
    }))
    updateConfig({ factors: redistributed })
  }

  const updateFactor = (id: string, updates: Partial<FactorConfig>) => {
    updateConfig({
      factors: config.factors.map(f => f.id === id ? { ...f, ...updates } : f)
    })
  }

  const addScoreRange = (factorId: string) => {
    const factor = config.factors.find(f => f.id === factorId)
    if (!factor) return

    const newRange: ScoreRange = { min: 0, max: 10, score: 3 }
    updateFactor(factorId, {
      scoreRanges: [...(factor.scoreRanges || []), newRange]
    })
  }

  const updateScoreRange = (factorId: string, index: number, updates: Partial<ScoreRange>) => {
    const factor = config.factors.find(f => f.id === factorId)
    if (!factor?.scoreRanges) return

    const newRanges = [...factor.scoreRanges]
    newRanges[index] = { ...newRanges[index], ...updates }
    updateFactor(factorId, { scoreRanges: newRanges })
  }

  const removeScoreRange = (factorId: string, index: number) => {
    const factor = config.factors.find(f => f.id === factorId)
    if (!factor?.scoreRanges) return

    updateFactor(factorId, {
      scoreRanges: factor.scoreRanges.filter((_, i) => i !== index)
    })
  }

  const factorsByCategory = FACTORS.reduce((acc, factor) => {
    if (!acc[factor.category]) acc[factor.category] = []
    acc[factor.category].push(factor)
    return acc
  }, {} as Record<string, typeof FACTORS[number][]>)

  return (
    <div className="space-y-8">
      {/* Selection Method */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Selection Method
        </label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { id: 'top_n', name: 'Top N by Factor', desc: 'Select top ranked securities' },
            { id: 'multi_factor', name: 'Multi-Factor Scoring', desc: 'Composite score from multiple factors' },
            { id: 'threshold', name: 'Threshold Based', desc: 'All securities meeting criteria' },
            { id: 'all', name: 'Include All', desc: 'All universe securities' },
          ].map(method => (
            <button
              key={method.id}
              onClick={() => updateConfig({ method: method.id as SelectionConfig['method'] })}
              className={`p-4 rounded-xl border-2 text-left transition-all ${config.method === method.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
                }`}
            >
              <div className="font-medium text-gray-900">{method.name}</div>
              <div className="text-xs text-gray-500 mt-1">{method.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Top N Setting */}
      {(config.method === 'top_n' || config.method === 'multi_factor') && (
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">
            Select Top
          </label>
          <input
            type="number"
            min="1"
            max="1000"
            value={config.topN || 50}
            onChange={(e) => updateConfig({ topN: Number(e.target.value) })}
            className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-gray-500">securities by composite score</span>
        </div>
      )}

      {/* Factors Configuration */}
      {config.method !== 'all' && (
        <div className="bg-gray-50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {config.method === 'multi_factor' ? 'Scoring Factors' : 'Ranking Factor'}
            </h3>
            <button
              onClick={() => setShowFactorModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Factor
            </button>
          </div>

          {config.factors.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No factors configured yet.</p>
              <p className="text-sm">Add factors to define how securities are ranked or scored.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {config.factors.map((factor) => (
                <div
                  key={factor.id}
                  className="bg-white rounded-lg border border-gray-200 p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="text-lg font-semibold text-gray-900">
                          {factor.name}
                        </span>
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {factor.field}
                        </span>
                      </div>

                      {/* Weight & Direction */}
                      <div className="flex items-center gap-6 mt-3">
                        <div className="flex items-center gap-2">
                          <label className="text-sm text-gray-600">Weight:</label>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={Math.round(factor.weight)}
                            onChange={(e) => updateFactor(factor.id, { weight: Number(e.target.value) })}
                            className="w-16 px-2 py-1 border rounded text-sm"
                          />
                          <span className="text-sm text-gray-500">%</span>
                        </div>

                        <div className="flex items-center gap-2">
                          <label className="text-sm text-gray-600">Direction:</label>
                          <select
                            value={factor.direction}
                            onChange={(e) => updateFactor(factor.id, { direction: e.target.value as 'asc' | 'desc' })}
                            className="px-2 py-1 border rounded text-sm"
                          >
                            <option value="desc">Higher is Better</option>
                            <option value="asc">Lower is Better</option>
                          </select>
                        </div>
                      </div>

                      {/* Score Ranges (for multi-factor) */}
                      {config.method === 'multi_factor' && (
                        <div className="mt-4">
                          <div className="flex items-center justify-between mb-2">
                            <label className="text-sm font-medium text-gray-700">
                              Score Ranges
                            </label>
                            <button
                              onClick={() => addScoreRange(factor.id)}
                              className="text-xs text-blue-600 hover:text-blue-800"
                            >
                              + Add Range
                            </button>
                          </div>

                          {factor.scoreRanges && factor.scoreRanges.length > 0 ? (
                            <div className="space-y-2">
                              {factor.scoreRanges.map((range, rangeIndex) => (
                                <div key={rangeIndex} className="flex items-center gap-2 text-sm">
                                  <input
                                    type="number"
                                    value={range.min ?? ''}
                                    onChange={(e) => updateScoreRange(factor.id, rangeIndex, {
                                      min: e.target.value === '' ? null : Number(e.target.value)
                                    })}
                                    placeholder="Min"
                                    className="w-20 px-2 py-1 border rounded"
                                  />
                                  <span className="text-gray-400">to</span>
                                  <input
                                    type="number"
                                    value={range.max ?? ''}
                                    onChange={(e) => updateScoreRange(factor.id, rangeIndex, {
                                      max: e.target.value === '' ? null : Number(e.target.value)
                                    })}
                                    placeholder="Max"
                                    className="w-20 px-2 py-1 border rounded"
                                  />
                                  <span className="text-gray-400">=</span>
                                  <input
                                    type="number"
                                    min="1"
                                    max="10"
                                    value={range.score}
                                    onChange={(e) => updateScoreRange(factor.id, rangeIndex, {
                                      score: Number(e.target.value)
                                    })}
                                    className="w-16 px-2 py-1 border rounded"
                                  />
                                  <span className="text-gray-500">pts</span>
                                  <button
                                    onClick={() => removeScoreRange(factor.id, rangeIndex)}
                                    className="text-red-500 hover:text-red-700"
                                  >
                                    ×
                                  </button>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-gray-400">
                              No score ranges defined. Factor will use linear ranking.
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => removeFactor(factor.id)}
                      className="text-gray-400 hover:text-red-600 p-1"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Buffer Rules */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Buffer Rules</h3>
        <p className="text-sm text-gray-500 mb-4">
          Buffer rules help reduce turnover by setting different thresholds for adding vs removing constituents.
        </p>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Add at Rank
            </label>
            <input
              type="number"
              value={config.bufferRules?.addThreshold || ''}
              onChange={(e) => updateConfig({
                bufferRules: {
                  ...config.bufferRules,
                  addThreshold: Number(e.target.value) || 0,
                  removeThreshold: config.bufferRules?.removeThreshold || 0
                }
              })}
              placeholder="e.g. 45"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <p className="text-xs text-gray-500 mt-1">
              New securities must rank this high to be added
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Remove at Rank
            </label>
            <input
              type="number"
              value={config.bufferRules?.removeThreshold || ''}
              onChange={(e) => updateConfig({
                bufferRules: {
                  ...config.bufferRules,
                  addThreshold: config.bufferRules?.addThreshold || 0,
                  removeThreshold: Number(e.target.value) || 0
                }
              })}
              placeholder="e.g. 60"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <p className="text-xs text-gray-500 mt-1">
              Existing constituents stay until they fall below this rank
            </p>
          </div>
        </div>
      </div>

      {/* Factor Selection Modal */}
      {showFactorModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold">Add Factor</h3>
                <button
                  onClick={() => setShowFactorModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              {Object.entries(factorsByCategory).map(([category, factors]) => (
                <div key={category} className="mb-6">
                  <h4 className="text-sm font-medium text-gray-500 mb-3">{category}</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {factors.map(factor => (
                      <button
                        key={factor.id}
                        onClick={() => addFactor(factor)}
                        className="text-left p-3 rounded-lg border border-gray-200 hover:border-blue-500 hover:bg-blue-50 transition-all"
                      >
                        <div className="font-medium text-gray-900">{factor.name}</div>
                        <div className="text-xs text-gray-500">{factor.field}</div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}



