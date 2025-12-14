import { IndexTemplate } from '../types'

export const indexTemplates: IndexTemplate[] = [
  {
    id: 'indexmaker-north-america',
    name: 'Indexmaker North America Large & Mid Cap',
    description: 'Large and mid-cap equities from the United States and Canada, weighted by free-float market cap with quarterly rebalancing.',
    category: 'geographic',
    icon: '🌎',
    config: {
      basics: {
        name: 'Indexmaker North America Large & Mid Cap',
        identifier: 'IMNAMC',
        description: 'North American large and mid-cap equity index',
        currency: 'USD',
        baseDate: new Date().toISOString().split('T')[0],
        baseValue: 1000,
      },
      universe: {
        assetClass: 'equities',
        countries: ['US', 'CA'],
        excludeCountries: [],
        sectors: [],
        excludeSectors: [],
        minMarketCap: 500_000_000,
        minAdtv: 1_000_000,
        minFreeFloat: 0.1,
      },
      selection: {
        method: 'top_n',
        topN: 500,
        factors: [
          { id: 'ff_mcap', name: 'Free Float Market Cap', field: 'freeFloatMarketCap', weight: 100, direction: 'desc' }
        ],
        bufferRules: {
          addThreshold: 450,
          removeThreshold: 550,
        },
      },
      weighting: {
        method: 'free_float_market_cap',
        maxWeight: 0.10,
      },
      rebalancing: {
        frequency: 'quarterly',
        announcementLead: 10,
      },
    },
  },
  {
    id: 'indexmaker-developed-europe',
    name: 'Indexmaker Developed Europe Large & Mid Cap',
    description: 'Large and mid-cap equities from developed European markets including UK, Germany, France, Switzerland, and more.',
    category: 'geographic',
    icon: '🇪🇺',
    config: {
      basics: {
        name: 'Indexmaker Developed Europe Large & Mid Cap',
        identifier: 'IMEUMC',
        description: 'Developed Europe large and mid-cap equity index',
        currency: 'EUR',
        baseDate: new Date().toISOString().split('T')[0],
        baseValue: 1000,
      },
      universe: {
        assetClass: 'equities',
        countries: ['GB', 'DE', 'FR', 'CH', 'NL', 'SE', 'IT', 'ES'],
        excludeCountries: [],
        sectors: [],
        excludeSectors: [],
        minMarketCap: 500_000_000,
        minAdtv: 500_000,
        minFreeFloat: 0.1,
      },
      selection: {
        method: 'top_n',
        topN: 350,
        factors: [
          { id: 'ff_mcap', name: 'Free Float Market Cap', field: 'freeFloatMarketCap', weight: 100, direction: 'desc' }
        ],
        bufferRules: {
          addThreshold: 300,
          removeThreshold: 400,
        },
      },
      weighting: {
        method: 'free_float_market_cap',
        maxWeight: 0.10,
      },
      rebalancing: {
        frequency: 'quarterly',
      },
    },
  },
  {
    id: 'faang-index',
    name: 'FAANG Technology Leaders',
    description: 'Concentrated index of leading technology companies (Meta, Apple, Amazon, Netflix, Google) with share class selection rules.',
    category: 'thematic',
    icon: '📱',
    config: {
      basics: {
        name: 'FAANG Technology Leaders',
        identifier: 'FAANG',
        description: 'Leading technology company index',
        currency: 'USD',
        baseDate: new Date().toISOString().split('T')[0],
        baseValue: 1000,
      },
      universe: {
        assetClass: 'equities',
        countries: ['US'],
        excludeCountries: [],
        sectors: ['technology', 'communication_services', 'consumer_discretionary'],
        excludeSectors: [],
        minMarketCap: 100_000_000_000,
      },
      selection: {
        method: 'threshold',
        factors: [
          { id: 'mcap', name: 'Market Cap', field: 'marketCap', weight: 100, direction: 'desc' }
        ],
      },
      weighting: {
        method: 'market_cap',
        maxWeight: 0.25,
      },
      rebalancing: {
        frequency: 'quarterly',
      },
    },
  },
  {
    id: 'subscription-economy',
    name: 'Subscription Economy Index',
    description: 'Multi-factor index targeting subscription-based business models with scoring on FCF, revenue growth, R&D intensity, and profitability.',
    category: 'thematic',
    icon: '🔄',
    config: {
      basics: {
        name: 'Subscription Economy Performance Index',
        identifier: 'SUBSEC',
        description: 'Companies with subscription-based recurring revenue models',
        currency: 'USD',
        baseDate: new Date().toISOString().split('T')[0],
        baseValue: 1000,
      },
      universe: {
        assetClass: 'equities',
        countries: ['US', 'CA', 'GB', 'DE', 'FR', 'CH', 'NL', 'SE'],
        excludeCountries: [],
        sectors: ['technology', 'communication_services', 'healthcare', 'consumer_discretionary'],
        excludeSectors: ['financials', 'energy', 'utilities', 'real_estate'],
        minMarketCap: 1_000_000_000,
        minAdtv: 5_000_000,
      },
      selection: {
        method: 'multi_factor',
        topN: 40,
        compositeScoring: true,
        factors: [
          {
            id: 'fcf_mcap',
            name: 'FCF / Market Cap',
            field: 'fcfYield',
            weight: 25,
            direction: 'desc',
            scoreRanges: [
              { min: 15, max: null, score: 5 },
              { min: 10, max: 15, score: 4 },
              { min: 5, max: 10, score: 3 },
              { min: 0, max: 5, score: 2 },
              { min: null, max: 0, score: 1 },
            ],
          },
          {
            id: 'rev_growth',
            name: 'Revenue Growth (3Y CAGR)',
            field: 'revenueGrowth3Y',
            weight: 25,
            direction: 'desc',
            scoreRanges: [
              { min: 30, max: null, score: 5 },
              { min: 20, max: 30, score: 4 },
              { min: 10, max: 20, score: 3 },
              { min: 0, max: 10, score: 2 },
              { min: null, max: 0, score: 1 },
            ],
          },
          {
            id: 'rd_sales',
            name: 'R&D / Sales',
            field: 'rdToSales',
            weight: 25,
            direction: 'desc',
            scoreRanges: [
              { min: 20, max: null, score: 5 },
              { min: 15, max: 20, score: 4 },
              { min: 10, max: 15, score: 3 },
              { min: 5, max: 10, score: 2 },
              { min: null, max: 5, score: 1 },
            ],
          },
          {
            id: 'gpm',
            name: 'Gross Profit Margin',
            field: 'grossMargin',
            weight: 25,
            direction: 'desc',
            scoreRanges: [
              { min: 70, max: null, score: 5 },
              { min: 60, max: 70, score: 4 },
              { min: 50, max: 60, score: 3 },
              { min: 40, max: 50, score: 2 },
              { min: null, max: 40, score: 1 },
            ],
          },
        ],
        sectorCaps: {
          technology: 8,
          communication_services: 8,
          healthcare: 8,
          consumer_discretionary: 8,
        },
        bufferRules: {
          addThreshold: 35,
          removeThreshold: 50,
        },
      },
      weighting: {
        method: 'equal',
      },
      rebalancing: {
        frequency: 'semi_annual',
      },
      validation: {
        minComponents: 30,
        maxComponents: 50,
        maxSectorWeight: 0.30,
      },
    },
  },
  {
    id: 'quality-growth',
    name: 'Quality Growth',
    description: 'Companies with high profitability metrics, strong balance sheets, and consistent earnings growth.',
    category: 'factor',
    icon: '💎',
    config: {
      basics: {
        name: 'Quality Growth Index',
        identifier: 'QGROW',
        description: 'High-quality companies with growth characteristics',
        currency: 'USD',
        baseDate: new Date().toISOString().split('T')[0],
        baseValue: 1000,
      },
      universe: {
        assetClass: 'equities',
        countries: ['US'],
        excludeCountries: [],
        sectors: [],
        excludeSectors: ['financials', 'real_estate'],
        minMarketCap: 5_000_000_000,
        minAdtv: 10_000_000,
      },
      selection: {
        method: 'multi_factor',
        topN: 50,
        compositeScoring: true,
        factors: [
          { id: 'roe', name: 'Return on Equity', field: 'roe', weight: 30, direction: 'desc' },
          { id: 'earnings_growth', name: 'Earnings Growth', field: 'earningsGrowth', weight: 30, direction: 'desc' },
          { id: 'debt_equity', name: 'Debt/Equity (lower is better)', field: 'debtToEquity', weight: 20, direction: 'asc' },
          { id: 'fcf_yield', name: 'FCF Yield', field: 'fcfYield', weight: 20, direction: 'desc' },
        ],
      },
      weighting: {
        method: 'market_cap',
        maxWeight: 0.05,
      },
      rebalancing: {
        frequency: 'quarterly',
      },
    },
  },
  {
    id: 'dividend-aristocrats',
    name: 'Dividend Aristocrats',
    description: 'Companies with 25+ years of consecutive dividend increases, weighted by dividend yield.',
    category: 'factor',
    icon: '💰',
    config: {
      basics: {
        name: 'Dividend Aristocrats Index',
        identifier: 'DIVARIST',
        description: 'Consistent dividend growth companies',
        currency: 'USD',
        baseDate: new Date().toISOString().split('T')[0],
        baseValue: 1000,
      },
      universe: {
        assetClass: 'equities',
        countries: ['US'],
        excludeCountries: [],
        sectors: [],
        excludeSectors: [],
        minMarketCap: 3_000_000_000,
        minAdtv: 5_000_000,
      },
      selection: {
        method: 'threshold',
        factors: [
          { id: 'div_years', name: 'Consecutive Dividend Years', field: 'dividendYears', weight: 100, direction: 'desc' },
        ],
      },
      weighting: {
        method: 'equal',
      },
      rebalancing: {
        frequency: 'annual',
      },
    },
  },
  {
    id: 'emerging-markets',
    name: 'Emerging Markets Large Cap',
    description: 'Large-cap equities from emerging market countries including China, India, Brazil, and more.',
    category: 'geographic',
    icon: '🌍',
    config: {
      basics: {
        name: 'Emerging Markets Large Cap',
        identifier: 'EMLC',
        description: 'Emerging market large-cap equity index',
        currency: 'USD',
        baseDate: new Date().toISOString().split('T')[0],
        baseValue: 1000,
      },
      universe: {
        assetClass: 'equities',
        countries: ['CN', 'IN', 'BR', 'KR', 'TW', 'ZA', 'MX'],
        excludeCountries: [],
        sectors: [],
        excludeSectors: [],
        minMarketCap: 2_000_000_000,
        minAdtv: 2_000_000,
        minFreeFloat: 0.15,
      },
      selection: {
        method: 'top_n',
        topN: 200,
        factors: [
          { id: 'ff_mcap', name: 'Free Float Market Cap', field: 'freeFloatMarketCap', weight: 100, direction: 'desc' }
        ],
      },
      weighting: {
        method: 'free_float_market_cap',
        maxWeight: 0.10,
      },
      rebalancing: {
        frequency: 'quarterly',
      },
    },
  },
  {
    id: 'blank',
    name: 'Start from Scratch',
    description: 'Build a completely custom index from the ground up with full control over all parameters.',
    category: 'custom',
    icon: '✨',
    config: {
      basics: {
        name: '',
        identifier: '',
        description: '',
        currency: 'USD',
        baseDate: new Date().toISOString().split('T')[0],
        baseValue: 1000,
      },
      universe: {
        assetClass: 'equities',
        countries: [],
        excludeCountries: [],
        sectors: [],
        excludeSectors: [],
      },
      selection: {
        method: 'top_n',
        topN: 50,
        factors: [],
      },
      weighting: {
        method: 'equal',
      },
      rebalancing: {
        frequency: 'quarterly',
      },
    },
  },
]

export const getTemplateById = (id: string): IndexTemplate | undefined => {
  return indexTemplates.find(t => t.id === id)
}

export const getTemplatesByCategory = (category: string): IndexTemplate[] => {
  return indexTemplates.filter(t => t.category === category)
}



