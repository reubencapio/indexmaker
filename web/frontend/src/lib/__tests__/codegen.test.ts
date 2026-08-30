/**
 * Tests for generated indexforge code.
 *
 * The snippet in the UI is something users copy and run, so the bar is that it
 * executes -- not that it looks plausible. These tests run over every built-in
 * template, because that is where the real bugs surfaced: a template with four
 * scoring factors silently produced a one-factor ranking, and a template with a
 * minimum market cap produced a Python tuple.
 *
 * The symbol lists mirror the library's enums. If indexforge adds or renames a
 * member, update them here; a mismatch means the generator can emit a name that
 * does not exist.
 */
import { describe, it, expect } from 'vitest'
import { indexTemplates } from '../../data/templates'
import { generatePythonCode, pythonNumber, FACTOR_MAP } from '../codegen'
import { IndexConfiguration } from '../../types'

const LIBRARY_FACTORS = new Set([
  'DEBT_TO_EQUITY', 'DIVIDEND_YIELD', 'EARNINGS_GROWTH', 'FREE_FLOAT_MARKET_CAP',
  'LIQUIDITY', 'LOW_VOLATILITY', 'MARKET_CAP', 'MOMENTUM', 'PRICE_TO_BOOK',
  'PRICE_TO_EARNINGS', 'QUALITY', 'REVENUE_GROWTH', 'ROA', 'ROE', 'VALUE', 'VOLUME',
])

const LIBRARY_SECTORS = new Set([
  'BASIC_MATERIALS', 'COMMUNICATION_SERVICES', 'CONSUMER_CYCLICAL', 'CONSUMER_DEFENSIVE',
  'CONSUMER_DISCRETIONARY', 'CONSUMER_STAPLES', 'ENERGY', 'FINANCIALS', 'FINANCIAL_SERVICES',
  'HEALTHCARE', 'HEALTH_CARE', 'INDUSTRIALS', 'INFORMATION_TECHNOLOGY', 'MATERIALS',
  'REAL_ESTATE', 'TECHNOLOGY', 'UTILITIES',
])

const LIBRARY_ASSET_CLASSES = new Set([
  'ALTERNATIVES', 'COMMODITIES', 'CURRENCIES', 'EQUITIES', 'FIXED_INCOME', 'MULTI_ASSET',
])

/** Builder methods that exist on the library's UniverseBuilder. */
const UNIVERSE_METHODS = new Set([
  'asset_class', 'regions', 'countries', 'exclude_countries', 'sectors', 'exclude_sectors',
  'industries', 'exchanges', 'tickers', 'min_market_cap', 'max_market_cap',
  'min_average_daily_volume', 'min_free_float', 'currency', 'esg_screening',
  'custom_filter', 'build',
])

function symbolsOf(code: string, enumName: string): string[] {
  return [...code.matchAll(new RegExp(`${enumName}\\.([A-Z_]+)`, 'g'))].map(m => m[1])
}

describe('pythonNumber', () => {
  it('never emits comma separators', () => {
    // toLocaleString produced "1,000,000,000", which Python reads as the tuple
    // (1, 0, 0, 0) and passes as four positional arguments.
    expect(pythonNumber(1_000_000_000)).not.toContain(',')
  })

  it('uses underscore grouping, which Python accepts', () => {
    expect(pythonNumber(1_000_000_000)).toBe('1_000_000_000')
    expect(pythonNumber(5_000_000)).toBe('5_000_000')
  })

  it('leaves small numbers alone', () => {
    expect(pythonNumber(40)).toBe('40')
    expect(pythonNumber(100)).toBe('100')
  })

  it('passes through non-integers', () => {
    expect(pythonNumber(0.25)).toBe('0.25')
  })
})

describe.each(indexTemplates.map(t => [t.id, t] as const))('template: %s', (_id, template) => {
  const code = generatePythonCode(template.config as IndexConfiguration)

  it('imports from indexforge, not indexmaker', () => {
    expect(code).toContain('from indexforge import')
    expect(code).not.toContain('from indexmaker import')
  })

  it('imports every library symbol it references', () => {
    const importBlock = code.slice(0, code.indexOf(')') + 1)
    for (const name of ['Index', 'Universe', 'AssetClass', 'Currency', 'Country', 'Sector', 'Factor', 'CompositeScore', 'SelectionCriteria', 'WeightingMethod', 'RebalancingSchedule']) {
      const usedInBody = new RegExp(`\\b${name}\\b`).test(code.slice(importBlock.length))
      if (usedInBody) {
        expect(importBlock, `${name} is used but not imported`).toContain(name)
      }
    }
  })

  it('emits no comma-separated numeric literals', () => {
    // Catches `min_market_cap(1,000,000,000)`.
    expect(code).not.toMatch(/\(\s*\d+,\d{3}/)
  })

  it('references only Factor members the library defines', () => {
    for (const symbol of symbolsOf(code, 'Factor')) {
      expect(LIBRARY_FACTORS.has(symbol), `Factor.${symbol} does not exist`).toBe(true)
    }
  })

  it('references only Sector members the library defines', () => {
    for (const symbol of symbolsOf(code, 'Sector')) {
      expect(LIBRARY_SECTORS.has(symbol), `Sector.${symbol} does not exist`).toBe(true)
    }
  })

  it('references only AssetClass members the library defines', () => {
    for (const symbol of symbolsOf(code, 'AssetClass')) {
      expect(LIBRARY_ASSET_CLASSES.has(symbol), `AssetClass.${symbol} does not exist`).toBe(true)
    }
  })

  it('calls only UniverseBuilder methods the library defines', () => {
    // Bound the slice to the universe statement itself. Anchoring on the next
    // comment instead would swallow the composite block, whose
    // CompositeScore.builder() is not a UniverseBuilder call.
    const open = code.indexOf('Universe.builder()') + 'Universe.builder()'.length
    const close = code.indexOf('\n)', open)
    const universeBlock = code.slice(open, close)
    for (const [, method] of universeBlock.matchAll(/\.([a-z_]+)\(/g)) {
      expect(UNIVERSE_METHODS.has(method), `.${method}() is not a UniverseBuilder method`).toBe(true)
    }
  })

  it('represents every configured factor', () => {
    // A factor is represented either by its library symbol (a single-factor
    // ranking) or by name (a weighted entry in a composite). Neither appearing
    // means it was silently dropped, which is what used to happen to every
    // factor after the first.
    const factors = (template.config.selection?.factors ?? []).filter(f => f.id !== 'blank')
    for (const factor of factors) {
      const symbol = FACTOR_MAP[factor.id]
      const represented =
        code.includes(factor.name) || (symbol !== undefined && code.includes(`Factor.${symbol}`))
      expect(represented, `factor "${factor.name}" (${factor.id}) was dropped`).toBe(true)
    }
  })

  it('emits the configured exclusions', () => {
    if ((template.config.universe?.excludeSectors?.length ?? 0) > 0) {
      expect(code).toContain('.exclude_sectors(')
    }
    if ((template.config.universe?.excludeCountries?.length ?? 0) > 0) {
      expect(code).toContain('.exclude_countries(')
    }
  })
})

describe('composite scoring', () => {
  const multiFactor = indexTemplates.filter(t => (t.config.selection?.factors?.length ?? 0) > 1)

  it('there is at least one multi-factor template to guard', () => {
    expect(multiFactor.length).toBeGreaterThan(0)
  })

  it.each(multiFactor.map(t => [t.id, t] as const))(
    '%s builds a CompositeScore rather than ranking on one factor',
    (_id, template) => {
      const code = generatePythonCode(template.config as IndexConfiguration)
      expect(code).toContain('CompositeScore.builder()')
      expect(code).toContain('.composite_score(score)')
      // The old generator emitted a bare ranking_by from factors[0] and dropped
      // the rest of the methodology.
      expect(code).not.toMatch(/^\s*\.ranking_by\(/m)
    }
  )

  it('weights every factor and sums them to one', () => {
    const template = multiFactor[0]
    const code = generatePythonCode(template.config as IndexConfiguration)
    const weights = [...code.matchAll(/weight=([0-9.]+)/g)].map(m => Number(m[1]))
    const total = weights.reduce((sum, w) => sum + w, 0)
    expect(weights.length).toBe(template.config.selection!.factors!.length)
    expect(total).toBeCloseTo(1, 3)
  })
})
