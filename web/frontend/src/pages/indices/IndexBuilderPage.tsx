import { useState, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { IndexTemplate, IndexConfiguration, IndexBasics } from '../../types'
import { indexTemplates } from '../../data/templates'
import { TemplateSelector } from '../../components/features/index-builder/TemplateSelector'
import { UniverseBuilder } from '../../components/features/index-builder/UniverseBuilder'
import { SelectionBuilder } from '../../components/features/index-builder/SelectionBuilder'
import { WeightingBuilder } from '../../components/features/index-builder/WeightingBuilder'
import { RebalancingBuilder } from '../../components/features/index-builder/RebalancingBuilder'
import { CodePreview } from '../../components/features/index-builder/CodePreview'
import { indicesApi, CreateIndexRequest } from '../../lib/api'

type Step = 'template' | 'basics' | 'universe' | 'selection' | 'weighting' | 'rebalancing' | 'review'

const STEPS: { id: Step; label: string; icon: string }[] = [
  { id: 'template', label: 'Template', icon: '📋' },
  { id: 'basics', label: 'Basics', icon: '📝' },
  { id: 'universe', label: 'Universe', icon: '🌍' },
  { id: 'selection', label: 'Selection', icon: '🎯' },
  { id: 'weighting', label: 'Weighting', icon: '⚖️' },
  { id: 'rebalancing', label: 'Rebalancing', icon: '🔄' },
  { id: 'review', label: 'Review', icon: '✅' },
]

export function IndexBuilderPage() {
  const { id } = useParams<{ id: string }>()
  const isEditMode = !!id
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState<Step>(isEditMode ? 'basics' : 'template')
  const [selectedTemplate, setSelectedTemplate] = useState<IndexTemplate | null>(null)
  const [config, setConfig] = useState<IndexConfiguration | null>(null)
  const [showCodePanel, setShowCodePanel] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Fetch existing index if in edit mode
  const { data: existingIndex, isLoading: isLoadingIndex } = useQuery({
    queryKey: ['index', id],
    queryFn: () => indicesApi.get(id!),
    enabled: isEditMode,
  })

  // Initialize config from existing index when editing
  useEffect(() => {
    if (existingIndex && !config) {
      // Convert backend index to frontend config format
      const loadedConfig: IndexConfiguration = {
        basics: {
          name: existingIndex.name,
          identifier: existingIndex.identifier,
          description: existingIndex.description || '',
          currency: existingIndex.currency,
          baseDate: existingIndex.base_date?.split('T')[0] || new Date().toISOString().split('T')[0],
          baseValue: existingIndex.base_value,
        },
        universe: {
          assetClass: 'EQUITIES',
          countries: existingIndex.countries || [],
          excludeCountries: [],
          sectors: existingIndex.sectors || [],
          excludeSectors: [],
          minMarketCap: existingIndex.min_market_cap,
          minAdtv: existingIndex.min_avg_volume,
        },
        selection: {
          method: 'top_n',
          topN: existingIndex.max_components || 50,
          factors: [{ id: 'market_cap', name: 'Market Cap', field: 'marketCap', weight: 1, direction: 'desc' }],
        },
        weighting: {
          method: existingIndex.weighting_method === 'equal_weight' ? 'equal' :
            existingIndex.weighting_method === 'market_cap' ? 'market_cap' :
              existingIndex.weighting_method === 'free_float_market_cap' ? 'free_float_market_cap' : 'market_cap',
          maxWeight: existingIndex.max_weight,
        },
        rebalancing: {
          frequency: (existingIndex.rebalance_frequency as any) || 'quarterly',
        },
        customRules: existingIndex.custom_rules,
      }
      setConfig(loadedConfig)
      setCurrentStep('basics')
    }
  }, [existingIndex, config])

  const handleTemplateSelect = (template: IndexTemplate) => {
    setSelectedTemplate(template)
    setConfig(JSON.parse(JSON.stringify(template.config))) // Deep clone
    setCurrentStep('basics')
  }

  const updateConfig = <K extends keyof IndexConfiguration>(
    key: K,
    value: IndexConfiguration[K]
  ) => {
    if (!config) return
    setConfig({ ...config, [key]: value })
  }

  const currentStepIndex = STEPS.findIndex(s => s.id === currentStep)
  const canGoBack = currentStepIndex > 0
  const canGoNext = currentStepIndex < STEPS.length - 1

  const goToStep = (step: Step) => {
    if (step === 'template' || config) {
      setCurrentStep(step)
    }
  }

  const goBack = () => {
    if (canGoBack) {
      setCurrentStep(STEPS[currentStepIndex - 1].id)
    }
  }

  const goNext = () => {
    if (canGoNext) {
      setCurrentStep(STEPS[currentStepIndex + 1].id)
    }
  }

  const handleSave = async () => {
    if (!config) return

    setIsSaving(true)
    setSaveError(null)

    try {
      if (isEditMode && id) {
        // Update existing index
        const updatePayload = {
          name: config.basics.name,
          description: config.basics.description || undefined,
          weighting_method: config.weighting.method === 'equal' ? 'equal_weight' :
            config.weighting.method === 'market_cap' ? 'market_cap' :
              config.weighting.method === 'free_float_market_cap' ? 'free_float_market_cap' :
                config.weighting.method,
          rebalance_frequency: config.rebalancing.frequency,
          custom_rules: config.customRules,
        }

        await indicesApi.update(id, updatePayload)
        navigate(`/indices/${id}`)
      } else {
        // Create new index
        const apiPayload: CreateIndexRequest = {
          name: config.basics.name,
          identifier: config.basics.identifier,
          description: config.basics.description || undefined,
          currency: config.basics.currency,
          base_date: config.basics.baseDate,
          base_value: config.basics.baseValue,
          weighting_method: config.weighting.method === 'equal' ? 'equal_weight' :
            config.weighting.method === 'market_cap' ? 'market_cap' :
              config.weighting.method === 'free_float_market_cap' ? 'free_float_market_cap' :
                config.weighting.method,
          rebalance_frequency: config.rebalancing.frequency,
          countries: config.universe.countries.length > 0 ? config.universe.countries : undefined,
          sectors: config.universe.sectors.length > 0 ? config.universe.sectors : undefined,
          min_market_cap: config.universe.minMarketCap,
          max_components: config.selection.topN || 100,
          max_weight: config.weighting.maxWeight,
          custom_rules: config.customRules,
        }

        const savedIndex = await indicesApi.create(apiPayload)
        navigate(`/indices/${savedIndex.id}`)
      }
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to save index'
      setSaveError(errorMessage)
      console.error('Failed to save index:', error)
    } finally {
      setIsSaving(false)
    }
  }

  // Show loading state when fetching existing index
  if (isEditMode && isLoadingIndex) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading index...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link to={isEditMode ? `/indices/${id}` : "/indices"} className="text-gray-500 hover:text-gray-700">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  {config?.basics.name || (isEditMode ? 'Edit Index' : 'New Index')}
                </h1>
                <p className="text-sm text-gray-500">
                  {isEditMode ? 'Edit Index Configuration' : (selectedTemplate ? `Based on: ${selectedTemplate.name}` : 'Index Builder')}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowCodePanel(!showCodePanel)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${showCodePanel
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                {showCodePanel ? 'Hide Code' : 'Show Code'}
              </button>

              {config && (
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSaving ? (
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                    </svg>
                  )}
                  {isSaving ? 'Saving...' : 'Save Index'}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Progress Steps */}
      {currentStep !== 'template' && (
        <div className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              {STEPS.slice(1).map((step, index) => {
                const stepIndex = index + 1
                const isActive = step.id === currentStep
                const isCompleted = currentStepIndex > stepIndex
                const isClickable = stepIndex <= currentStepIndex + 1

                return (
                  <div key={step.id} className="flex items-center flex-1">
                    <button
                      onClick={() => isClickable && goToStep(step.id)}
                      disabled={!isClickable}
                      className={`flex items-center gap-2 ${isClickable ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
                        }`}
                    >
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition-colors ${isActive
                            ? 'bg-blue-600 text-white'
                            : isCompleted
                              ? 'bg-green-500 text-white'
                              : 'bg-gray-200 text-gray-600'
                          }`}
                      >
                        {isCompleted ? '✓' : step.icon}
                      </div>
                      <span
                        className={`text-sm font-medium hidden sm:block ${isActive ? 'text-blue-600' : 'text-gray-600'
                          }`}
                      >
                        {step.label}
                      </span>
                    </button>
                    {index < STEPS.length - 2 && (
                      <div
                        className={`flex-1 h-0.5 mx-4 ${isCompleted ? 'bg-green-500' : 'bg-gray-200'
                          }`}
                      />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className={`flex ${showCodePanel && config ? 'divide-x' : ''}`}>
        {/* Form Panel */}
        <div className={`flex-1 ${showCodePanel && config ? 'w-3/5' : 'w-full'}`}>
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Template Selection */}
            {currentStep === 'template' && (
              <TemplateSelector onSelect={handleTemplateSelect} />
            )}

            {/* Basics */}
            {currentStep === 'basics' && config && (
              <div className="space-y-8">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Basic Information</h2>
                  <p className="text-gray-600">Define the core properties of your index</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Index Name *
                    </label>
                    <input
                      type="text"
                      value={config.basics.name}
                      onChange={(e) => updateConfig('basics', { ...config.basics, name: e.target.value })}
                      placeholder="e.g. My Custom Index"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Identifier *
                    </label>
                    <input
                      type="text"
                      value={config.basics.identifier}
                      onChange={(e) => updateConfig('basics', { ...config.basics, identifier: e.target.value.toUpperCase() })}
                      placeholder="e.g. MYIDX"
                      maxLength={10}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 uppercase"
                    />
                    <p className="text-xs text-gray-500 mt-1">Unique ticker symbol (max 10 chars)</p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description
                    </label>
                    <textarea
                      value={config.basics.description}
                      onChange={(e) => updateConfig('basics', { ...config.basics, description: e.target.value })}
                      rows={3}
                      placeholder="Describe your index methodology..."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Currency
                    </label>
                    <select
                      value={config.basics.currency}
                      onChange={(e) => updateConfig('basics', { ...config.basics, currency: e.target.value })}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="USD">USD - US Dollar</option>
                      <option value="EUR">EUR - Euro</option>
                      <option value="GBP">GBP - British Pound</option>
                      <option value="JPY">JPY - Japanese Yen</option>
                      <option value="CHF">CHF - Swiss Franc</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Base Date
                    </label>
                    <input
                      type="date"
                      value={config.basics.baseDate}
                      onChange={(e) => updateConfig('basics', { ...config.basics, baseDate: e.target.value })}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Base Value
                    </label>
                    <input
                      type="number"
                      value={config.basics.baseValue}
                      onChange={(e) => updateConfig('basics', { ...config.basics, baseValue: Number(e.target.value) })}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Usually 100 or 1000</p>
                  </div>
                </div>
              </div>
            )}

            {/* Universe */}
            {currentStep === 'universe' && config && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Define Universe</h2>
                  <p className="text-gray-600">Specify which securities are eligible for your index</p>
                </div>
                <UniverseBuilder
                  config={config.universe}
                  onChange={(universe) => updateConfig('universe', universe)}
                />
              </div>
            )}

            {/* Selection */}
            {currentStep === 'selection' && config && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Selection Criteria</h2>
                  <p className="text-gray-600">Define how constituents are selected from the universe</p>
                </div>
                <SelectionBuilder
                  config={config.selection}
                  onChange={(selection) => updateConfig('selection', selection)}
                />
              </div>
            )}

            {/* Weighting */}
            {currentStep === 'weighting' && config && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Weighting Method</h2>
                  <p className="text-gray-600">Choose how constituent weights are determined</p>
                </div>
                <WeightingBuilder
                  config={config.weighting}
                  onChange={(weighting) => updateConfig('weighting', weighting)}
                />
              </div>
            )}

            {/* Rebalancing */}
            {currentStep === 'rebalancing' && config && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Rebalancing Schedule</h2>
                  <p className="text-gray-600">Set when and how often the index is rebalanced</p>
                </div>
                <RebalancingBuilder
                  config={config.rebalancing}
                  onChange={(rebalancing) => updateConfig('rebalancing', rebalancing)}
                />
              </div>
            )}

            {/* Review */}
            {currentStep === 'review' && config && (
              <div className="space-y-8">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Review Configuration</h2>
                  <p className="text-gray-600">Review your index settings before saving</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Summary cards */}
                  <div className="bg-white rounded-xl border p-6">
                    <h3 className="font-semibold text-gray-900 mb-4">📝 Basic Information</h3>
                    <dl className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Name</dt>
                        <dd className="text-gray-900 font-medium">{config.basics.name}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Identifier</dt>
                        <dd className="text-gray-900 font-medium">{config.basics.identifier}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Currency</dt>
                        <dd className="text-gray-900">{config.basics.currency}</dd>
                      </div>
                    </dl>
                  </div>

                  <div className="bg-white rounded-xl border p-6">
                    <h3 className="font-semibold text-gray-900 mb-4">🌍 Universe</h3>
                    <dl className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Countries</dt>
                        <dd className="text-gray-900">{config.universe.countries.length || 'All'}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Sectors</dt>
                        <dd className="text-gray-900">{config.universe.sectors.length || 'All'}</dd>
                      </div>
                    </dl>
                  </div>

                  <div className="bg-white rounded-xl border p-6">
                    <h3 className="font-semibold text-gray-900 mb-4">🎯 Selection</h3>
                    <dl className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Method</dt>
                        <dd className="text-gray-900">{config.selection.method}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Factors</dt>
                        <dd className="text-gray-900">{config.selection.factors.length}</dd>
                      </div>
                    </dl>
                  </div>

                  <div className="bg-white rounded-xl border p-6">
                    <h3 className="font-semibold text-gray-900 mb-4">⚖️ Weighting</h3>
                    <dl className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Method</dt>
                        <dd className="text-gray-900">{config.weighting.method}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Max Weight</dt>
                        <dd className="text-gray-900">{config.weighting.maxWeight ? `${config.weighting.maxWeight * 100}%` : 'No limit'}</dd>
                      </div>
                    </dl>
                  </div>
                </div>

                {saveError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                    <p className="font-medium">Error saving index</p>
                    <p className="text-sm">{saveError}</p>
                  </div>
                )}

                <div className="flex justify-center">
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 px-8 py-4 bg-green-600 text-white rounded-xl hover:bg-green-700 text-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSaving ? (
                      <>
                        <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Saving...
                      </>
                    ) : (
                      <>
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {isEditMode ? 'Update Index' : 'Create Index'}
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Navigation */}
            {currentStep !== 'template' && (
              <div className="flex items-center justify-between mt-12 pt-8 border-t">
                <button
                  onClick={goBack}
                  disabled={!canGoBack}
                  className={`flex items-center gap-2 px-6 py-3 rounded-lg transition-colors ${canGoBack
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      : 'bg-gray-50 text-gray-400 cursor-not-allowed'
                    }`}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Previous
                </button>

                {currentStep !== 'review' ? (
                  <button
                    onClick={goNext}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Next
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                ) : null}
              </div>
            )}
          </div>
        </div>

        {/* Code Preview Panel */}
        {showCodePanel && config && (
          <div className="w-2/5 bg-gray-900 sticky top-32 h-[calc(100vh-8rem)] overflow-hidden">
            <CodePreview config={config} />
          </div>
        )}
      </div>
    </div>
  )
}
