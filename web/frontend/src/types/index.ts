// Index Builder Types

export interface IndexTemplate {
  id: string
  name: string
  description: string
  category: 'geographic' | 'thematic' | 'factor' | 'custom'
  icon: string
  config: IndexConfiguration
}

export interface IndexConfiguration {
  basics: IndexBasics
  universe: UniverseConfig
  selection: SelectionConfig
  weighting: WeightingConfig
  rebalancing: RebalancingConfig
  validation?: ValidationConfig
}

export interface IndexBasics {
  name: string
  identifier: string
  description: string
  currency: string
  baseDate: string
  baseValue: number
}

export interface UniverseConfig {
  assetClass: string
  countries: string[]
  excludeCountries: string[]
  sectors: string[]
  excludeSectors: string[]
  minMarketCap?: number
  maxMarketCap?: number
  minAdtv?: number
  minFreeFloat?: number
  exchanges?: string[]
}

export interface SelectionConfig {
  method: 'top_n' | 'multi_factor' | 'threshold' | 'all'
  topN?: number
  factors: FactorConfig[]
  sectorCaps?: Record<string, number>
  bufferRules?: BufferRules
  compositeScoring?: boolean
}

export interface FactorConfig {
  id: string
  name: string
  field: string
  weight: number
  direction: 'asc' | 'desc'
  scoreRanges?: ScoreRange[]
}

export interface ScoreRange {
  min: number | null
  max: number | null
  score: number
}

export interface BufferRules {
  addThreshold: number
  removeThreshold: number
}

export interface WeightingConfig {
  method: 'equal' | 'market_cap' | 'free_float_market_cap' | 'factor' | 'custom'
  maxWeight?: number
  minWeight?: number
  factorField?: string
  customWeights?: Record<string, number>
}

export interface RebalancingConfig {
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'semi_annual' | 'annual'
  effectiveDate?: string
  announcementLead?: number
  referenceDateOffset?: number
}

export interface ValidationConfig {
  minComponents?: number
  maxComponents?: number
  maxSectorWeight?: number
  maxCountryWeight?: number
  maxSingleWeight?: number
}

// Country and Sector data
export const COUNTRIES = {
  // North America
  US: { code: 'US', name: 'United States', region: 'North America', flag: '🇺🇸' },
  CA: { code: 'CA', name: 'Canada', region: 'North America', flag: '🇨🇦' },
  MX: { code: 'MX', name: 'Mexico', region: 'North America', flag: '🇲🇽' },
  // Europe
  GB: { code: 'GB', name: 'United Kingdom', region: 'Europe', flag: '🇬🇧' },
  DE: { code: 'DE', name: 'Germany', region: 'Europe', flag: '🇩🇪' },
  FR: { code: 'FR', name: 'France', region: 'Europe', flag: '🇫🇷' },
  CH: { code: 'CH', name: 'Switzerland', region: 'Europe', flag: '🇨🇭' },
  NL: { code: 'NL', name: 'Netherlands', region: 'Europe', flag: '🇳🇱' },
  SE: { code: 'SE', name: 'Sweden', region: 'Europe', flag: '🇸🇪' },
  IT: { code: 'IT', name: 'Italy', region: 'Europe', flag: '🇮🇹' },
  ES: { code: 'ES', name: 'Spain', region: 'Europe', flag: '🇪🇸' },
  // Asia Pacific
  JP: { code: 'JP', name: 'Japan', region: 'Asia Pacific', flag: '🇯🇵' },
  AU: { code: 'AU', name: 'Australia', region: 'Asia Pacific', flag: '🇦🇺' },
  HK: { code: 'HK', name: 'Hong Kong', region: 'Asia Pacific', flag: '🇭🇰' },
  SG: { code: 'SG', name: 'Singapore', region: 'Asia Pacific', flag: '🇸🇬' },
  KR: { code: 'KR', name: 'South Korea', region: 'Asia Pacific', flag: '🇰🇷' },
  TW: { code: 'TW', name: 'Taiwan', region: 'Asia Pacific', flag: '🇹🇼' },
  CN: { code: 'CN', name: 'China', region: 'Asia Pacific', flag: '🇨🇳' },
  IN: { code: 'IN', name: 'India', region: 'Asia Pacific', flag: '🇮🇳' },
  // Emerging Markets
  BR: { code: 'BR', name: 'Brazil', region: 'Latin America', flag: '🇧🇷' },
  ZA: { code: 'ZA', name: 'South Africa', region: 'Africa', flag: '🇿🇦' },
} as const

export const SECTORS = [
  { id: 'technology', name: 'Technology', icon: '💻' },
  { id: 'healthcare', name: 'Healthcare', icon: '🏥' },
  { id: 'financials', name: 'Financials', icon: '🏦' },
  { id: 'consumer_discretionary', name: 'Consumer Discretionary', icon: '🛍️' },
  { id: 'consumer_staples', name: 'Consumer Staples', icon: '🛒' },
  { id: 'industrials', name: 'Industrials', icon: '🏭' },
  { id: 'energy', name: 'Energy', icon: '⚡' },
  { id: 'materials', name: 'Materials', icon: '🧱' },
  { id: 'utilities', name: 'Utilities', icon: '💡' },
  { id: 'real_estate', name: 'Real Estate', icon: '🏢' },
  { id: 'communication_services', name: 'Communication Services', icon: '📡' },
] as const

export const FACTORS = [
  // Fundamentals
  { id: 'market_cap', name: 'Market Capitalization', category: 'Size', field: 'marketCap' },
  { id: 'free_float_market_cap', name: 'Free Float Market Cap', category: 'Size', field: 'freeFloatMarketCap' },
  { id: 'revenue', name: 'Revenue', category: 'Fundamentals', field: 'revenue' },
  { id: 'revenue_growth', name: 'Revenue Growth (YoY)', category: 'Growth', field: 'revenueGrowth' },
  { id: 'revenue_growth_3y', name: 'Revenue Growth (3Y CAGR)', category: 'Growth', field: 'revenueGrowth3Y' },
  { id: 'earnings_growth', name: 'Earnings Growth', category: 'Growth', field: 'earningsGrowth' },
  // Profitability
  { id: 'gross_margin', name: 'Gross Profit Margin', category: 'Profitability', field: 'grossMargin' },
  { id: 'operating_margin', name: 'Operating Margin', category: 'Profitability', field: 'operatingMargin' },
  { id: 'net_margin', name: 'Net Profit Margin', category: 'Profitability', field: 'netMargin' },
  { id: 'roe', name: 'Return on Equity (ROE)', category: 'Profitability', field: 'roe' },
  { id: 'roa', name: 'Return on Assets (ROA)', category: 'Profitability', field: 'roa' },
  { id: 'roic', name: 'Return on Invested Capital', category: 'Profitability', field: 'roic' },
  // Cash Flow
  { id: 'fcf', name: 'Free Cash Flow', category: 'Cash Flow', field: 'freeCashFlow' },
  { id: 'fcf_yield', name: 'FCF Yield', category: 'Cash Flow', field: 'fcfYield' },
  { id: 'fcf_margin', name: 'FCF / Revenue', category: 'Cash Flow', field: 'fcfMargin' },
  { id: 'cash_ratio', name: 'Cash / Market Cap', category: 'Cash Flow', field: 'cashRatio' },
  // Valuation
  { id: 'pe_ratio', name: 'P/E Ratio', category: 'Valuation', field: 'peRatio' },
  { id: 'pb_ratio', name: 'P/B Ratio', category: 'Valuation', field: 'pbRatio' },
  { id: 'ps_ratio', name: 'P/S Ratio', category: 'Valuation', field: 'psRatio' },
  { id: 'ev_ebitda', name: 'EV/EBITDA', category: 'Valuation', field: 'evEbitda' },
  // Quality
  { id: 'rd_sales', name: 'R&D / Sales', category: 'Quality', field: 'rdToSales' },
  { id: 'debt_equity', name: 'Debt / Equity', category: 'Quality', field: 'debtToEquity' },
  { id: 'current_ratio', name: 'Current Ratio', category: 'Quality', field: 'currentRatio' },
  // Momentum
  { id: 'price_return_1m', name: 'Price Return (1M)', category: 'Momentum', field: 'priceReturn1M' },
  { id: 'price_return_3m', name: 'Price Return (3M)', category: 'Momentum', field: 'priceReturn3M' },
  { id: 'price_return_12m', name: 'Price Return (12M)', category: 'Momentum', field: 'priceReturn12M' },
  // Liquidity
  { id: 'adtv', name: 'Avg Daily Trading Volume', category: 'Liquidity', field: 'adtv' },
  { id: 'adtv_20d', name: 'ADTV (20-day)', category: 'Liquidity', field: 'adtv20' },
] as const



