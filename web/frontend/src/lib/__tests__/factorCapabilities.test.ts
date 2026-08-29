/**
 * Tests for factor availability in the UI.
 *
 * The picker offers 28 factors; the engine computes 7. These pin the behaviour
 * that stops the other 21 being selectable and then silently scoring every
 * constituent the same.
 */
import { describe, it, expect } from 'vitest'
import { FACTORS } from '../../types'
import {
  Capabilities,
  UI_FACTOR_TO_LIBRARY,
  factorAvailability,
} from '../factorCapabilities'

const CAPABILITIES: Capabilities = {
  data_source: 'Yahoo Finance',
  factors: [
    { factor: 'MARKET_CAP', available: true, higher_is_better: true, missing_fields: [], reason: null },
    { factor: 'PRICE_TO_EARNINGS', available: true, higher_is_better: false, missing_fields: [], reason: null },
    {
      factor: 'PRICE_TO_BOOK',
      available: false,
      higher_is_better: false,
      missing_fields: ['pb_ratio'],
      reason: 'Not provided by OpenBB: pb_ratio',
    },
    { factor: 'REVENUE_GROWTH', available: false, higher_is_better: null, missing_fields: [], reason: 'Not yet implemented' },
  ],
}

describe('factorAvailability', () => {
  it('marks a computable factor available', () => {
    expect(factorAvailability('market_cap', CAPABILITIES).available).toBe(true)
  })

  it('reports lowest-first ranking for valuation ratios', () => {
    expect(factorAvailability('pe_ratio', CAPABILITIES).reason).toBe('Ranked lowest-first')
  })

  it('passes through the data-source reason', () => {
    const result = factorAvailability('pb_ratio', CAPABILITIES)
    expect(result.available).toBe(false)
    expect(result.reason).toContain('OpenBB')
  })

  it('reports unimplemented factors as such', () => {
    const result = factorAvailability('revenue_growth', CAPABILITIES)
    expect(result.available).toBe(false)
    expect(result.reason).toBe('Not yet implemented')
  })

  it('rejects UI factors the engine has no concept of', () => {
    // fcf_yield, roic, ev_ebitda and friends exist only in the picker.
    const result = factorAvailability('fcf_yield', CAPABILITIES)
    expect(result.available).toBe(false)
    expect(result.reason).toBe('Not supported by the index engine')
  })

  it('fails closed while capabilities are loading', () => {
    // Briefly withholding a working factor beats offering one that does nothing.
    expect(factorAvailability('market_cap', undefined).available).toBe(false)
  })

  it('fails closed for a factor absent from the response', () => {
    const sparse: Capabilities = { data_source: 'X', factors: [] }
    expect(factorAvailability('market_cap', sparse).available).toBe(false)
  })
})

describe('id mapping', () => {
  it('every mapped UI id exists in the picker', () => {
    const pickerIds = new Set<string>(FACTORS.map(f => f.id))
    for (const uiId of Object.keys(UI_FACTOR_TO_LIBRARY)) {
      expect(pickerIds.has(uiId), `${uiId} is mapped but not offered`).toBe(true)
    }
  })

  it('maps to SCREAMING_SNAKE library names', () => {
    for (const name of Object.values(UI_FACTOR_TO_LIBRARY)) {
      expect(name).toMatch(/^[A-Z][A-Z_]*$/)
    }
  })

  it('most of the picker is not computable, and that is reported not hidden', () => {
    const unavailable = FACTORS.filter(f => !factorAvailability(f.id, CAPABILITIES).available)
    expect(unavailable.length).toBeGreaterThan(FACTORS.length / 2)
  })
})
