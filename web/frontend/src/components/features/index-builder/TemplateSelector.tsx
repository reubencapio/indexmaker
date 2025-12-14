import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { IndexTemplate } from '../../../types'
import { indexTemplates } from '../../../data/templates'
import { aiApi, AIGenerateResponse } from '../../../lib/api'

interface TemplateSelectorProps {
  onSelect: (template: IndexTemplate) => void
}

const categoryLabels: Record<string, string> = {
  geographic: '🌍 Geographic',
  thematic: '🎯 Thematic',
  factor: '📊 Factor-Based',
  custom: '✨ Custom',
}

export function TemplateSelector({ onSelect }: TemplateSelectorProps) {
  const navigate = useNavigate()
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [hoveredTemplate, setHoveredTemplate] = useState<string | null>(null)
  const [showAIModal, setShowAIModal] = useState(false)
  const [aiDescription, setAiDescription] = useState('')
  const [aiResult, setAiResult] = useState<AIGenerateResponse | null>(null)

  // Check if AI is available
  const { data: aiStatus } = useQuery({
    queryKey: ['ai-status'],
    queryFn: aiApi.status,
  })

  // AI generation mutation
  const generateMutation = useMutation({
    mutationFn: aiApi.generate,
    onSuccess: (data) => {
      setAiResult(data)
    },
  })

  // AI create mutation
  const createMutation = useMutation({
    mutationFn: aiApi.create,
    onSuccess: (data) => {
      navigate(`/indices/${data.id}`)
    },
  })

  const categories = [...new Set(indexTemplates.map(t => t.category))]
  
  const filteredTemplates = selectedCategory
    ? indexTemplates.filter(t => t.category === selectedCategory)
    : indexTemplates

  const handleAIGenerate = () => {
    if (!aiDescription.trim()) return
    generateMutation.mutate({ description: aiDescription })
  }

  const handleAICreate = () => {
    if (!aiDescription.trim()) return
    createMutation.mutate({ description: aiDescription })
  }

  const handleUseAIResult = () => {
    if (!aiResult) return
    
    // Convert AI result to template format
    const template: IndexTemplate = {
      id: 'ai-generated',
      name: aiResult.index.name,
      description: aiResult.explanation,
      category: 'custom',
      icon: '🤖',
      config: {
        basics: {
          name: aiResult.index.name,
          identifier: aiResult.index.identifier,
          description: aiResult.index.description,
          currency: aiResult.index.currency,
          baseDate: aiResult.index.base_date,
          baseValue: aiResult.index.base_value,
        },
        universe: {
          assetClass: 'EQUITIES',
          countries: aiResult.index.countries,
          excludeCountries: [],
          sectors: aiResult.index.sectors,
          excludeSectors: [],
          tickers: aiResult.index.tickers,
          minMarketCap: aiResult.index.min_market_cap,
        },
        selection: {
          method: 'top_n',
          topN: aiResult.index.max_components,
          factors: [{ id: 'market_cap', name: 'Market Cap', field: 'marketCap', weight: 1, direction: 'desc' as const }],
        },
        weighting: {
          method: aiResult.index.weighting_method === 'equal_weight' ? 'equal' : 
                  aiResult.index.weighting_method === 'free_float_market_cap' ? 'free_float_market_cap' : 'market_cap',
          maxWeight: aiResult.index.max_weight,
        },
        rebalancing: {
          frequency: aiResult.index.rebalance_frequency as 'monthly' | 'quarterly' | 'semi_annual' | 'annual',
        },
      },
    }
    
    setShowAIModal(false)
    onSelect(template)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900">Choose a Starting Point</h2>
        <p className="mt-2 text-gray-600">
          Select a template based on your investment methodology, or start from scratch
        </p>
      </div>

      {/* AI Creation Card - Featured */}
      {aiStatus?.available && (
        <div 
          onClick={() => setShowAIModal(true)}
          className="relative cursor-pointer rounded-2xl border-2 border-dashed border-purple-300 bg-gradient-to-br from-purple-50 to-indigo-50 p-8 transition-all duration-200 hover:border-purple-500 hover:shadow-lg hover:scale-[1.01]"
        >
          <div className="flex items-start gap-6">
            <div className="flex-shrink-0">
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center text-3xl shadow-lg">
                ✨
              </div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-xl font-bold text-gray-900">Create with AI</h3>
                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-semibold rounded-full">
                  NEW
                </span>
              </div>
              <p className="text-gray-600 mb-4">
                Describe your ideal index in plain English and let AI create it for you. 
                Just say something like "Top 30 US technology companies, equal weighted" or 
                "European dividend aristocrats with ESG screening".
              </p>
              <div className="flex items-center gap-2 text-sm text-purple-600 font-medium">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Powered by {aiStatus.provider === 'gemini' ? 'Google Gemini' : 'OpenAI'}
              </div>
            </div>
            <div className="flex-shrink-0">
              <span className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg font-medium shadow hover:bg-purple-700 transition-colors">
                Try it now
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Category Filter */}
      <div className="flex justify-center gap-3">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
            selectedCategory === null
              ? 'bg-blue-600 text-white shadow-md'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All Templates
        </button>
        {categories.map(category => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
              selectedCategory === category
                ? 'bg-blue-600 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {categoryLabels[category]}
          </button>
        ))}
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredTemplates.map(template => (
          <div
            key={template.id}
            onClick={() => onSelect(template)}
            onMouseEnter={() => setHoveredTemplate(template.id)}
            onMouseLeave={() => setHoveredTemplate(null)}
            className={`relative cursor-pointer rounded-xl border-2 p-6 transition-all duration-200 ${
              hoveredTemplate === template.id
                ? 'border-blue-500 shadow-lg scale-[1.02] bg-blue-50/50'
                : 'border-gray-200 hover:border-gray-300 bg-white'
            }`}
          >
            {/* Icon */}
            <div className="text-4xl mb-4">{template.icon}</div>
            
            {/* Title */}
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {template.name}
            </h3>
            
            {/* Description */}
            <p className="text-sm text-gray-600 line-clamp-3">
              {template.description}
            </p>
            
            {/* Category Badge */}
            <div className="mt-4">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                template.category === 'geographic' ? 'bg-green-100 text-green-800' :
                template.category === 'thematic' ? 'bg-purple-100 text-purple-800' :
                template.category === 'factor' ? 'bg-orange-100 text-orange-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {categoryLabels[template.category]}
              </span>
            </div>

            {/* Hover Overlay */}
            {hoveredTemplate === template.id && (
              <div className="absolute inset-0 flex items-center justify-center bg-blue-600/10 rounded-xl">
                <span className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium shadow-lg">
                  Use This Template →
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Import Option */}
      <div className="border-t pt-8">
        <div className="flex items-center justify-center gap-4 text-gray-500">
          <span>Or</span>
          <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Import Configuration (JSON/YAML)
          </button>
        </div>
      </div>

      {/* AI Modal */}
      {showAIModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">✨</span>
                  <h3 className="text-xl font-bold text-white">Create Index with AI</h3>
                </div>
                <button 
                  onClick={() => {
                    setShowAIModal(false)
                    setAiResult(null)
                    setAiDescription('')
                  }}
                  className="text-white/80 hover:text-white"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-12rem)]">
              {!aiResult ? (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Describe your index
                    </label>
                    <textarea
                      value={aiDescription}
                      onChange={(e) => setAiDescription(e.target.value)}
                      placeholder="e.g., Create an equal-weight index of the top 20 US technology companies with a 10% maximum weight per stock, rebalancing quarterly"
                      rows={4}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    />
                  </div>

                  {/* Example Prompts */}
                  <div>
                    <p className="text-sm text-gray-500 mb-3">Try one of these examples:</p>
                    <div className="flex flex-wrap gap-2">
                      {[
                        'Top 30 US large-cap tech stocks, market cap weighted',
                        'European dividend aristocrats with ESG screening',
                        'FAANG stocks equal weighted',
                        'Global clean energy index with 50 constituents',
                      ].map((example) => (
                        <button
                          key={example}
                          onClick={() => setAiDescription(example)}
                          className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-sm text-gray-700 transition-colors"
                        >
                          {example}
                        </button>
                      ))}
                    </div>
                  </div>

                  {generateMutation.isError && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                      <p className="font-medium">Error generating index</p>
                      <p className="text-sm">{(generateMutation.error as Error)?.message || 'Something went wrong'}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Generated Index Preview */}
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-green-700 mb-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="font-medium">Index Generated Successfully</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-500 mb-1">Name</p>
                      <p className="font-semibold text-gray-900">{aiResult.index.name}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-500 mb-1">Identifier</p>
                      <p className="font-semibold text-gray-900">{aiResult.index.identifier}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-500 mb-1">Weighting</p>
                      <p className="font-semibold text-gray-900 capitalize">{aiResult.index.weighting_method.replace('_', ' ')}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-500 mb-1">Components</p>
                      <p className="font-semibold text-gray-900">{aiResult.index.max_components}</p>
                    </div>
                  </div>

                  {aiResult.index.tickers && aiResult.index.tickers.length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-500 mb-2">Tickers</p>
                      <div className="flex flex-wrap gap-2">
                        {aiResult.index.tickers.map(ticker => (
                          <span key={ticker} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-medium">
                            {ticker}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="bg-purple-50 rounded-lg p-4">
                    <p className="text-sm text-purple-700 font-medium mb-1">AI Explanation</p>
                    <p className="text-sm text-purple-900">{aiResult.explanation}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-gray-50 border-t flex justify-end gap-3">
              {!aiResult ? (
                <>
                  <button
                    onClick={() => setShowAIModal(false)}
                    className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAIGenerate}
                    disabled={!aiDescription.trim() || generateMutation.isPending}
                    className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {generateMutation.isPending ? (
                      <>
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Generating...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Generate Index
                      </>
                    )}
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => {
                      setAiResult(null)
                      setAiDescription('')
                    }}
                    className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    Start Over
                  </button>
                  <button
                    onClick={handleUseAIResult}
                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    Customize in Builder
                  </button>
                  <button
                    onClick={handleAICreate}
                    disabled={createMutation.isPending}
                    className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {createMutation.isPending ? (
                      <>
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Creating...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Create Now
                      </>
                    )}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
