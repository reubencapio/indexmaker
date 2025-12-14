import { useState } from 'react'
import { IndexTemplate } from '../../../types'
import { indexTemplates } from '../../../data/templates'

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
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [hoveredTemplate, setHoveredTemplate] = useState<string | null>(null)

  const categories = [...new Set(indexTemplates.map(t => t.category))]
  
  const filteredTemplates = selectedCategory
    ? indexTemplates.filter(t => t.category === selectedCategory)
    : indexTemplates

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900">Choose a Starting Point</h2>
        <p className="mt-2 text-gray-600">
          Select a template based on your investment methodology, or start from scratch
        </p>
      </div>

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
    </div>
  )
}



