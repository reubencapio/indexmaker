/**
 * Maps the UI's factor list onto the engine's factor registry.
 *
 * The picker offers 28 factors; the engine computes 7. Everything else used to be
 * selectable and then scored every constituent identically, which looks like a
 * working index and is not one. This module is what lets the picker say so.
 *
 * The authority is the backend's /capabilities endpoint, which derives from the
 * indexforge registry. This file only holds the id translation, because the UI,
 * the templates and the library each grew their own vocabulary.
 */

/** UI factor id -> library Factor name. Absent means the engine has no such concept. */
export const UI_FACTOR_TO_LIBRARY: Record<string, string> = {
  market_cap: 'MARKET_CAP',
  free_float_market_cap: 'FREE_FLOAT_MARKET_CAP',
  revenue_growth: 'REVENUE_GROWTH',
  revenue_growth_3y: 'REVENUE_GROWTH',
  earnings_growth: 'EARNINGS_GROWTH',
  roe: 'ROE',
  roa: 'ROA',
  pe_ratio: 'PRICE_TO_EARNINGS',
  pb_ratio: 'PRICE_TO_BOOK',
  debt_equity: 'DEBT_TO_EQUITY',
  adtv: 'LIQUIDITY',
  adtv_20d: 'LIQUIDITY',
  price_return_1m: 'MOMENTUM',
  price_return_3m: 'MOMENTUM',
  price_return_12m: 'MOMENTUM',
}

/** Factor ids used by the built-in templates, which use a third set of names. */
export const TEMPLATE_FACTOR_TO_LIBRARY: Record<string, string> = {
  mcap: 'MARKET_CAP',
  ff_mcap: 'FREE_FLOAT_MARKET_CAP',
  rev_growth: 'REVENUE_GROWTH',
  earnings_growth: 'EARNINGS_GROWTH',
  roe: 'ROE',
  debt_equity: 'DEBT_TO_EQUITY',
}

export interface FactorCapability {
  factor: string
  available: boolean
  higher_is_better: boolean | null
  missing_fields: string[]
  reason: string | null
}

export interface Capabilities {
  data_source: string
  factors: FactorCapability[]
}

export interface FactorAvailability {
  available: boolean
  reason: string
}

/**
 * Whether a UI factor can actually be computed right now.
 *
 * Fails closed: while capabilities are still loading, or when a factor has no
 * library equivalent at all, it is reported unavailable. Offering a factor that
 * does nothing is worse than briefly withholding one that works.
 */
export function factorAvailability(
  uiFactorId: string,
  capabilities: Capabilities | undefined
): FactorAvailability {
  const libraryName = UI_FACTOR_TO_LIBRARY[uiFactorId]

  if (!libraryName) {
    return { available: false, reason: 'Not supported by the index engine' }
  }

  if (!capabilities) {
    return { available: false, reason: 'Checking availability…' }
  }

  const entry = capabilities.factors.find(f => f.factor === libraryName)
  if (!entry) {
    return { available: false, reason: 'Not supported by the index engine' }
  }

  return {
    available: entry.available,
    reason: entry.available
      ? entry.higher_is_better === false
        ? 'Ranked lowest-first'
        : 'Available'
      : entry.reason ?? 'Unavailable',
  }
}
