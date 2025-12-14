import { useState } from 'react'
import { IndexConfiguration, COUNTRIES, SECTORS } from '../../../types'

interface CodePreviewProps {
  config: IndexConfiguration
}

type CodeFormat = 'python' | 'yaml' | 'json'

export function CodePreview({ config }: CodePreviewProps) {
  const [format, setFormat] = useState<CodeFormat>('python')
  const [copied, setCopied] = useState(false)

  const generatePythonCode = (): string => {
    const lines: string[] = []
    
    // Imports
    lines.push('from indexmaker import (')
    lines.push('    Index, Universe, SelectionCriteria, WeightingMethod,')
    lines.push('    RebalancingSchedule, ValidationRules, Country, Currency, Factor')
    lines.push(')')
    lines.push('')
    
    // Index creation
    lines.push('# Create the index')
    lines.push(`index = Index.create(`)
    lines.push(`    name="${config.basics.name}",`)
    lines.push(`    identifier="${config.basics.identifier}",`)
    lines.push(`    currency=Currency.${config.basics.currency},`)
    lines.push(`    base_date="${config.basics.baseDate}",`)
    lines.push(`    base_value=${config.basics.baseValue}`)
    lines.push(')')
    lines.push('')

    // Universe
    lines.push('# Define the universe')
    lines.push('universe = (Universe.builder()')
    lines.push(`    .asset_class("${config.universe.assetClass.toUpperCase()}")`)
    
    if (config.universe.countries.length > 0) {
      const countries = config.universe.countries
        .map(c => `Country.${c}`)
        .join(', ')
      lines.push(`    .countries([${countries}])`)
    }
    
    if (config.universe.sectors.length > 0) {
      const sectors = config.universe.sectors
        .map(s => `"${SECTORS.find(sec => sec.id === s)?.name}"`)
        .join(', ')
      lines.push(`    .sectors([${sectors}])`)
    }
    
    if (config.universe.minMarketCap) {
      lines.push(`    .min_market_cap(${config.universe.minMarketCap.toLocaleString()})`)
    }
    
    if (config.universe.minAdtv) {
      lines.push(`    .min_adtv(${config.universe.minAdtv.toLocaleString()})`)
    }
    
    if (config.universe.minFreeFloat) {
      lines.push(`    .min_free_float(${config.universe.minFreeFloat})`)
    }
    
    lines.push('    .build()')
    lines.push(')')
    lines.push('')

    // Selection Criteria
    if (config.selection.method !== 'all') {
      lines.push('# Selection criteria')
      lines.push('selection = (SelectionCriteria.builder()')
      
      if (config.selection.factors.length > 0) {
        const factor = config.selection.factors[0]
        lines.push(`    .ranking_by(Factor.${factor.field.toUpperCase()})`)
      }
      
      if (config.selection.topN) {
        lines.push(`    .select_top(${config.selection.topN})`)
      }
      
      if (config.selection.bufferRules) {
        lines.push(`    .apply_buffer_rules(`)
        lines.push(`        add_threshold=${config.selection.bufferRules.addThreshold},`)
        lines.push(`        remove_threshold=${config.selection.bufferRules.removeThreshold}`)
        lines.push(`    )`)
      }
      
      lines.push('    .build()')
      lines.push(')')
      lines.push('')
    }

    // Weighting
    lines.push('# Weighting method')
    if (config.weighting.method === 'equal') {
      lines.push('weighting = WeightingMethod.equal_weight()')
    } else if (config.weighting.method === 'market_cap') {
      if (config.weighting.maxWeight) {
        lines.push('weighting = (WeightingMethod.market_cap()')
        lines.push(`    .with_cap(max_weight=${config.weighting.maxWeight})`)
        lines.push('    .build()')
        lines.push(')')
      } else {
        lines.push('weighting = WeightingMethod.market_cap()')
      }
    } else if (config.weighting.method === 'free_float_market_cap') {
      if (config.weighting.maxWeight) {
        lines.push('weighting = (WeightingMethod.free_float_market_cap()')
        lines.push(`    .with_cap(max_weight=${config.weighting.maxWeight})`)
        lines.push('    .build()')
        lines.push(')')
      } else {
        lines.push('weighting = WeightingMethod.free_float_market_cap()')
      }
    }
    lines.push('')

    // Rebalancing
    lines.push('# Rebalancing schedule')
    const freqMap: Record<string, string> = {
      'daily': 'daily',
      'weekly': 'weekly',
      'monthly': 'monthly',
      'quarterly': 'quarterly',
      'semi_annual': 'semi_annual',
      'annual': 'annual'
    }
    lines.push(`rebalancing = RebalancingSchedule.${freqMap[config.rebalancing.frequency]}()`)
    lines.push('')

    // Configure the index
    lines.push('# Configure the index')
    lines.push('(index')
    lines.push('    .set_universe(universe)')
    if (config.selection.method !== 'all') {
      lines.push('    .set_selection_criteria(selection)')
    }
    lines.push('    .set_weighting_method(weighting)')
    lines.push('    .set_rebalancing_schedule(rebalancing)')
    lines.push(')')
    lines.push('')

    // Example usage
    lines.push('# Get constituents')
    lines.push('constituents = index.get_constituents()')
    lines.push('for c in constituents:')
    lines.push('    print(f"{c.ticker}: {c.name} - {c.weight:.2%}")')

    return lines.join('\n')
  }

  const generateYAML = (): string => {
    const yaml: string[] = []
    
    yaml.push('# Index Configuration')
    yaml.push(`name: "${config.basics.name}"`)
    yaml.push(`identifier: "${config.basics.identifier}"`)
    yaml.push(`currency: ${config.basics.currency}`)
    yaml.push(`base_date: "${config.basics.baseDate}"`)
    yaml.push(`base_value: ${config.basics.baseValue}`)
    yaml.push('')
    
    yaml.push('universe:')
    yaml.push(`  asset_class: ${config.universe.assetClass}`)
    if (config.universe.countries.length > 0) {
      yaml.push('  countries:')
      config.universe.countries.forEach(c => {
        yaml.push(`    - ${COUNTRIES[c as keyof typeof COUNTRIES]?.name || c}`)
      })
    }
    if (config.universe.sectors.length > 0) {
      yaml.push('  sectors:')
      config.universe.sectors.forEach(s => {
        yaml.push(`    - ${SECTORS.find(sec => sec.id === s)?.name || s}`)
      })
    }
    if (config.universe.minMarketCap) {
      yaml.push(`  min_market_cap: ${config.universe.minMarketCap}`)
    }
    if (config.universe.minAdtv) {
      yaml.push(`  min_adtv: ${config.universe.minAdtv}`)
    }
    yaml.push('')

    yaml.push('selection:')
    yaml.push(`  method: ${config.selection.method}`)
    if (config.selection.topN) {
      yaml.push(`  top_n: ${config.selection.topN}`)
    }
    if (config.selection.factors.length > 0) {
      yaml.push('  factors:')
      config.selection.factors.forEach(f => {
        yaml.push(`    - name: ${f.name}`)
        yaml.push(`      field: ${f.field}`)
        yaml.push(`      weight: ${f.weight}`)
        yaml.push(`      direction: ${f.direction}`)
        if (f.scoreRanges && f.scoreRanges.length > 0) {
          yaml.push('      score_ranges:')
          f.scoreRanges.forEach(r => {
            yaml.push(`        - min: ${r.min ?? 'null'}`)
            yaml.push(`          max: ${r.max ?? 'null'}`)
            yaml.push(`          score: ${r.score}`)
          })
        }
      })
    }
    if (config.selection.bufferRules) {
      yaml.push('  buffer_rules:')
      yaml.push(`    add_threshold: ${config.selection.bufferRules.addThreshold}`)
      yaml.push(`    remove_threshold: ${config.selection.bufferRules.removeThreshold}`)
    }
    yaml.push('')

    yaml.push('weighting:')
    yaml.push(`  method: ${config.weighting.method}`)
    if (config.weighting.maxWeight) {
      yaml.push(`  max_weight: ${config.weighting.maxWeight}`)
    }
    if (config.weighting.minWeight) {
      yaml.push(`  min_weight: ${config.weighting.minWeight}`)
    }
    yaml.push('')

    yaml.push('rebalancing:')
    yaml.push(`  frequency: ${config.rebalancing.frequency}`)
    if (config.rebalancing.announcementLead) {
      yaml.push(`  announcement_lead: ${config.rebalancing.announcementLead}`)
    }

    return yaml.join('\n')
  }

  const generateJSON = (): string => {
    return JSON.stringify(config, null, 2)
  }

  const getCode = (): string => {
    switch (format) {
      case 'python':
        return generatePythonCode()
      case 'yaml':
        return generateYAML()
      case 'json':
        return generateJSON()
    }
  }

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(getCode())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadFile = () => {
    const code = getCode()
    const ext = format === 'python' ? 'py' : format
    const filename = `${config.basics.identifier || 'index'}.${ext}`
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-gray-50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Generated Code</span>
          <div className="flex bg-gray-200 rounded-lg p-0.5">
            {(['python', 'yaml', 'json'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFormat(f)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  format === f
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            {copied ? (
              <>
                <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied!
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </>
            )}
          </button>
          <button
            onClick={downloadFile}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download
          </button>
        </div>
      </div>

      {/* Code Area */}
      <div className="flex-1 overflow-auto bg-gray-900 p-4">
        <pre className="text-sm font-mono text-gray-100 whitespace-pre-wrap">
          <code>{getCode()}</code>
        </pre>
      </div>
    </div>
  )
}



