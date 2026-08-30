import { IndexConfiguration, COUNTRIES, SECTORS } from '../types'

/**
 * Generates runnable indexforge code from an index configuration.
 *
 * Extracted from CodePreview so it can be tested directly. The snippet is
 * something users copy and run, so the bar is that it executes against the real
 * library -- not that it merely looks plausible. Anything the library cannot
 * express is emitted as an explicit comment rather than silently dropped.
 */

/** Template factor ids that map onto a built-in library Factor. */
export const FACTOR_MAP: Record<string, string> = {
  mcap: 'MARKET_CAP',
  ff_mcap: 'FREE_FLOAT_MARKET_CAP',
  earnings_growth: 'EARNINGS_GROWTH',
  rev_growth: 'REVENUE_GROWTH',
  roe: 'ROE',
  roa: 'ROA',
  debt_equity: 'DEBT_TO_EQUITY',
  momentum: 'MOMENTUM',
  value: 'VALUE',
  quality: 'QUALITY',
  low_vol: 'LOW_VOLATILITY',
  dividend_yield: 'DIVIDEND_YIELD',
  liquidity: 'LIQUIDITY',
  volume: 'VOLUME',
  pe: 'PRICE_TO_EARNINGS',
  pb: 'PRICE_TO_BOOK',
}

/**
 * Constituent attributes the library actually exposes. A factor whose field is
 * not here has no data behind it, so the generated code says so instead of
 * producing a lambda that quietly scores every company zero.
 */
const CONSTITUENT_FIELDS = new Set([
  'market_cap',
  'free_float_market_cap',
  'price',
  'revenue',
  'earnings',
  'dividend_yield',
  'pe_ratio',
  'pb_ratio',
  'average_daily_volume',
  'free_float_factor',
  'esg_score',
])

const COUNTRY_MAP: Record<string, string> = {
  US: 'UNITED_STATES',
  GB: 'UNITED_KINGDOM',
  DE: 'GERMANY',
  FR: 'FRANCE',
  CH: 'SWITZERLAND',
  NL: 'NETHERLANDS',
  SE: 'SWEDEN',
  IT: 'ITALY',
  ES: 'SPAIN',
  DK: 'DENMARK',
  FI: 'FINLAND',
  NO: 'NORWAY',
  BE: 'BELGIUM',
  IE: 'IRELAND',
  AT: 'AUSTRIA',
  PT: 'PORTUGAL',
  CA: 'CANADA',
  JP: 'JAPAN',
  AU: 'AUSTRALIA',
  HK: 'HONG_KONG',
  SG: 'SINGAPORE',
  KR: 'SOUTH_KOREA',
  TW: 'TAIWAN',
  CN: 'CHINA',
  IN: 'INDIA',
  BR: 'BRAZIL',
  MX: 'MEXICO',
  ZA: 'SOUTH_AFRICA',
}

const SECTOR_MAP: Record<string, string> = {
  Energy: 'ENERGY',
  Materials: 'MATERIALS',
  Industrials: 'INDUSTRIALS',
  Utilities: 'UTILITIES',
  'Health Care': 'HEALTH_CARE',
  Financials: 'FINANCIALS',
  'Consumer Discretionary': 'CONSUMER_DISCRETIONARY',
  'Consumer Staples': 'CONSUMER_STAPLES',
  'Information Technology': 'INFORMATION_TECHNOLOGY',
  'Communication Services': 'COMMUNICATION_SERVICES',
  'Real Estate': 'REAL_ESTATE',
  Technology: 'TECHNOLOGY',
  Healthcare: 'HEALTHCARE',
}

/**
 * Format a number as a Python literal.
 *
 * Never use toLocaleString here: its thousands separators turn
 * `min_market_cap(1000000000)` into `min_market_cap(1,000,000,000)`, which Python
 * parses as the tuple (1, 0, 0, 0) and passes as four positional arguments.
 * Underscores are the readable form Python actually accepts.
 */
export function pythonNumber(value: number): string {
  if (!Number.isFinite(value)) return '0'
  if (!Number.isInteger(value)) return String(value)
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, '_')
}

function pythonString(value: string): string {
  return `"${value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`
}

function sectorSymbol(sector: string): string {
  const known = SECTOR_MAP[sector]
  if (known) return known
  const label = SECTORS.find(s => s.id === sector)?.name
  return SECTOR_MAP[label ?? ''] ?? sector.toUpperCase().replace(/\s+/g, '_')
}

function countrySymbol(code: string): string {
  return COUNTRY_MAP[code] ?? code.toUpperCase()
}

export function generatePythonCode(config: IndexConfiguration): string {
  const lines: string[] = []
  const { universe, selection, weighting, rebalancing, basics } = config

  const usesSelection = selection.method !== 'all'
  const factors = selection.factors ?? []
  // A composite is warranted whenever more than one factor carries weight, or the
  // template asked for one. Emitting only factors[0] as a plain ranking silently
  // discards the rest of the methodology.
  const useComposite = usesSelection && (selection.compositeScoring || factors.length > 1)

  // Index creation
  lines.push('# Create the index')
  lines.push('index = Index.create(')
  lines.push(`    name=${pythonString(basics.name)},`)
  lines.push(`    identifier=${pythonString(basics.identifier)},`)
  lines.push(`    currency=Currency.${basics.currency},`)
  lines.push(`    base_date=${pythonString(basics.baseDate)},`)
  lines.push(`    base_value=${pythonNumber(basics.baseValue)},`)
  lines.push(')')
  lines.push('')

  // Universe
  lines.push('# Define the universe')
  lines.push('universe = (Universe.builder()')
  lines.push(`    .asset_class(AssetClass.${universe.assetClass.toUpperCase()})`)

  if (universe.countries.length > 0) {
    const countries = universe.countries.map(c => `Country.${countrySymbol(c)}`).join(', ')
    lines.push(`    .countries([${countries}])`)
  }
  if ((universe.excludeCountries?.length ?? 0) > 0) {
    const excluded = universe.excludeCountries.map(c => `Country.${countrySymbol(c)}`).join(', ')
    lines.push(`    .exclude_countries([${excluded}])`)
  }
  if (universe.sectors.length > 0) {
    const sectors = universe.sectors.map(s => `Sector.${sectorSymbol(s)}`).join(', ')
    lines.push(`    .sectors([${sectors}])`)
  }
  if ((universe.excludeSectors?.length ?? 0) > 0) {
    const excluded = universe.excludeSectors.map(s => `Sector.${sectorSymbol(s)}`).join(', ')
    lines.push(`    .exclude_sectors([${excluded}])`)
  }
  if (universe.minMarketCap) {
    lines.push(`    .min_market_cap(${pythonNumber(universe.minMarketCap)})`)
  }
  if (universe.maxMarketCap) {
    lines.push(`    .max_market_cap(${pythonNumber(universe.maxMarketCap)})`)
  }
  if (universe.minAdtv) {
    // The builder method is min_average_daily_volume; there is no min_adtv.
    lines.push(`    .min_average_daily_volume(${pythonNumber(universe.minAdtv)})`)
  }
  if (universe.minFreeFloat) {
    lines.push(`    .min_free_float(${universe.minFreeFloat})`)
  }
  lines.push('    .build()')
  lines.push(')')
  lines.push('')

  // Selection criteria
  if (usesSelection) {
    const unmapped = factors.filter(f => !FACTOR_MAP[f.id])

    if (useComposite) {
      lines.push('# Composite score across the weighted factors')
      lines.push('score = (CompositeScore.builder()')
      const totalWeight = factors.reduce((sum, f) => sum + (f.weight || 0), 0) || 1
      for (const factor of factors) {
        // Library weights are fractions; template weights are percentage points.
        const weight = ((factor.weight || 0) / totalWeight).toFixed(4)
        const ascending = factor.direction === 'asc' ? ', ascending=True' : ''
        const symbol = FACTOR_MAP[factor.id]
        if (symbol) {
          lines.push(`    .add_factor(Factor.${symbol}, weight=${weight}${ascending})  # ${factor.name}`)
        } else {
          const field = factor.field.replace(/([A-Z])/g, '_$1').toLowerCase()
          const available = CONSTITUENT_FIELDS.has(field)
          lines.push(
            `    # ${factor.name}: no built-in Factor for "${factor.id}".` +
              (available ? '' : ` Constituent has no "${field}" field, so this needs a data source.`)
          )
          lines.push(
            `    .add_custom_factor(${pythonString(factor.name)}, ` +
              `lambda c: getattr(c, "${field}", 0.0) or 0.0, weight=${weight})`
          )
        }
        if (factor.scoreRanges?.length) {
          lines.push(
            `    # Score bands defined in the UI are not yet expressible here; ` +
              `${factor.name} is scored continuously.`
          )
        }
      }
      lines.push('    .build()')
      lines.push(')')
      lines.push('')
    }

    lines.push('# Selection criteria')
    lines.push('selection = (SelectionCriteria.builder()')

    if (useComposite) {
      lines.push('    .composite_score(score)')
    } else if (factors.length > 0) {
      const factor = factors[0]
      const symbol = FACTOR_MAP[factor.id]
      if (symbol) {
        lines.push(`    .ranking_by(Factor.${symbol})`)
      } else {
        lines.push(`    # No built-in Factor matches "${factor.id}" (${factor.name}).`)
        lines.push('    .ranking_by(Factor.MARKET_CAP)  # placeholder ranking')
      }
    }

    if (selection.topN) {
      lines.push(`    .select_top(${selection.topN})`)
    }

    if (selection.bufferRules) {
      lines.push('    .apply_buffer_rules(')
      lines.push(`        add_threshold=${selection.bufferRules.addThreshold},`)
      lines.push(`        remove_threshold=${selection.bufferRules.removeThreshold},`)
      lines.push('    )')
    }

    if (config.customRules?.min_dividend_yield) {
      const value = config.customRules.min_dividend_yield
      lines.push(`    # Filter: minimum dividend yield >= ${(value * 100).toFixed(1)}%`)
      lines.push(`    .custom_filter(lambda c: (c.dividend_yield or 0) >= ${value})`)
    }
    if (config.customRules?.min_esg_score) {
      const value = config.customRules.min_esg_score
      lines.push(`    # Filter: minimum ESG score >= ${value}`)
      lines.push(`    .custom_filter(lambda c: (c.esg_score or 0) >= ${value})`)
    }

    if (selection.themeKeywords && selection.themeKeywords.length > 0) {
      const keywords = selection.themeKeywords.map(pythonString).join(', ')
      lines.push('    # Thematic filter: companies with matching business descriptions')
      lines.push(`    .theme_filter([${keywords}])`)
    } else if (unmapped.length === 0 && selection.method === 'multi_factor') {
      lines.push(
        '    # This index selects its theme from business descriptions at build time,'
      )
      lines.push('    # so there is no keyword filter to express here.')
    }

    lines.push('    .build()')
    lines.push(')')
    lines.push('')
  }

  // Weighting
  lines.push('# Weighting method')
  if (weighting.method === 'equal') {
    lines.push('weighting = WeightingMethod.equal_weight()')
  } else if (weighting.method === 'market_cap' || weighting.method === 'free_float_market_cap') {
    const factory = weighting.method === 'market_cap' ? 'market_cap' : 'free_float_market_cap'
    if (weighting.maxWeight) {
      lines.push(`weighting = (WeightingMethod.${factory}()`)
      lines.push(`    .with_cap(max_weight=${weighting.maxWeight})`)
      lines.push('    .build()')
      lines.push(')')
    } else {
      lines.push(`weighting = WeightingMethod.${factory}()`)
    }
  } else {
    lines.push(`# "${weighting.method}" weighting has no direct builder; equal weight stands in.`)
    lines.push('weighting = WeightingMethod.equal_weight()')
  }
  lines.push('')

  // Rebalancing
  lines.push('# Rebalancing schedule')
  lines.push(`rebalancing = RebalancingSchedule.${rebalancing.frequency}()`)
  lines.push('')

  // Wire it together
  lines.push('# Configure the index')
  lines.push('(index')
  lines.push('    .set_universe(universe)')
  if (usesSelection) {
    lines.push('    .set_selection_criteria(selection)')
  }
  lines.push('    .set_weighting_method(weighting)')
  lines.push('    .set_rebalancing_schedule(rebalancing)')
  lines.push(')')
  lines.push('')

  lines.push('# Get constituents')
  lines.push('constituents = index.get_constituents()')
  lines.push('for c in constituents:')
  lines.push('    print(f"{c.ticker}: {c.name} - {c.weight:.2%}")')

  return [...importLines(lines), '', ...lines].join('\n')
}

/**
 * Derive the import statement from the names the body actually uses.
 *
 * Deriving rather than predicting: an earlier version decided the imports from
 * the config separately from the code that emitted the references, and the two
 * drifted -- a placeholder `Factor.MARKET_CAP` on an unmapped factor produced a
 * NameError because that branch had not been accounted for in the import list.
 */
function importLines(body: string[]): string[] {
  const source = body.join('\n')
  const candidates = [
    'Index',
    'Universe',
    'SelectionCriteria',
    'CompositeScore',
    'WeightingMethod',
    'RebalancingSchedule',
    'AssetClass',
    'Currency',
    'Country',
    'Sector',
    'Factor',
  ]

  // Word-boundary match so `Index` is not claimed by `IndexError`, and
  // `SelectionCriteria` does not also count as a hit for a shorter name.
  const used = candidates.filter(name => new RegExp(`\\b${name}\\b`).test(source))

  const lines = ['from indexforge import (']
  for (let i = 0; i < used.length; i += 4) {
    lines.push(`    ${used.slice(i, i + 4).join(', ')},`)
  }
  lines.push(')')
  return lines
}

export function generateYAML(config: IndexConfiguration): string {
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
  if ((config.universe.excludeCountries?.length ?? 0) > 0) {
    yaml.push('  exclude_countries:')
    config.universe.excludeCountries.forEach(c => {
      yaml.push(`    - ${COUNTRIES[c as keyof typeof COUNTRIES]?.name || c}`)
    })
  }
  if (config.universe.sectors.length > 0) {
    yaml.push('  sectors:')
    config.universe.sectors.forEach(s => {
      yaml.push(`    - ${SECTORS.find(sec => sec.id === s)?.name || s}`)
    })
  }
  if ((config.universe.excludeSectors?.length ?? 0) > 0) {
    yaml.push('  exclude_sectors:')
    config.universe.excludeSectors.forEach(s => {
      yaml.push(`    - ${SECTORS.find(sec => sec.id === s)?.name || s}`)
    })
  }
  if (config.universe.minMarketCap) {
    yaml.push(`  min_market_cap: ${config.universe.minMarketCap}`)
  }
  if (config.universe.minAdtv) {
    yaml.push(`  min_average_daily_volume: ${config.universe.minAdtv}`)
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
  if (config.selection.themeKeywords?.length) {
    yaml.push('  theme_keywords:')
    config.selection.themeKeywords.forEach(k => yaml.push(`    - ${k}`))
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
