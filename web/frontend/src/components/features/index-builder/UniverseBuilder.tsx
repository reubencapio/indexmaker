import { useState } from 'react'
import { UniverseConfig, COUNTRIES, SECTORS } from '../../../types'

interface UniverseBuilderProps {
  config: UniverseConfig
  onChange: (config: UniverseConfig) => void
}

export function UniverseBuilder({ config, onChange }: UniverseBuilderProps) {
  const [countryMode, setCountryMode] = useState<'include' | 'exclude'>(
    config.excludeCountries.length > 0 ? 'exclude' : 'include'
  )

  const updateConfig = (updates: Partial<UniverseConfig>) => {
    onChange({ ...config, ...updates })
  }

  const toggleCountry = (code: string) => {
    const targetList = countryMode === 'include' ? 'countries' : 'excludeCountries'
    const currentList = config[targetList]
    
    if (currentList.includes(code)) {
      updateConfig({ [targetList]: currentList.filter(c => c !== code) })
    } else {
      updateConfig({ [targetList]: [...currentList, code] })
    }
  }

  const toggleSector = (id: string) => {
    if (config.sectors.includes(id)) {
      updateConfig({ sectors: config.sectors.filter(s => s !== id) })
    } else {
      updateConfig({ sectors: [...config.sectors, id] })
    }
  }

  const countriesByRegion = Object.values(COUNTRIES).reduce((acc, country) => {
    if (!acc[country.region]) acc[country.region] = []
    acc[country.region].push(country)
    return acc
  }, {} as Record<string, typeof COUNTRIES[keyof typeof COUNTRIES][]>)

  const formatNumber = (value: number | undefined) => {
    if (!value) return ''
    if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
    return value.toString()
  }

  return (
    <div className="space-y-8">
      {/* Asset Class */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Asset Class
        </label>
        <div className="flex gap-3">
          {['equities', 'fixed_income', 'commodities', 'multi_asset'].map(asset => (
            <button
              key={asset}
              onClick={() => updateConfig({ assetClass: asset })}
              className={`px-4 py-2 rounded-lg border-2 transition-all ${
                config.assetClass === asset
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              {asset === 'equities' && '📈 Equities'}
              {asset === 'fixed_income' && '📉 Fixed Income'}
              {asset === 'commodities' && '🛢️ Commodities'}
              {asset === 'multi_asset' && '📊 Multi-Asset'}
            </button>
          ))}
        </div>
      </div>

      {/* Geographic Filter */}
      <div className="bg-gray-50 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Geographic Filter</h3>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setCountryMode('include')
                updateConfig({ excludeCountries: [] })
              }}
              className={`px-3 py-1 rounded-md text-sm ${
                countryMode === 'include'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Include
            </button>
            <button
              onClick={() => {
                setCountryMode('exclude')
                updateConfig({ countries: [] })
              }}
              className={`px-3 py-1 rounded-md text-sm ${
                countryMode === 'exclude'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Exclude
            </button>
          </div>
        </div>

        {/* Quick Select */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => {
              const allCodes = Object.keys(COUNTRIES)
              updateConfig({ 
                countries: countryMode === 'include' ? allCodes : [],
                excludeCountries: countryMode === 'exclude' ? allCodes : []
              })
            }}
            className="text-xs px-2 py-1 bg-gray-200 rounded hover:bg-gray-300"
          >
            Select All
          </button>
          <button
            onClick={() => updateConfig({ countries: [], excludeCountries: [] })}
            className="text-xs px-2 py-1 bg-gray-200 rounded hover:bg-gray-300"
          >
            Clear All
          </button>
          <button
            onClick={() => updateConfig({ 
              countries: countryMode === 'include' ? ['US', 'CA'] : [],
              excludeCountries: countryMode === 'exclude' ? ['US', 'CA'] : []
            })}
            className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
          >
            North America
          </button>
          <button
            onClick={() => updateConfig({ 
              countries: countryMode === 'include' ? ['GB', 'DE', 'FR', 'CH', 'NL', 'SE', 'IT', 'ES'] : [],
              excludeCountries: countryMode === 'exclude' ? ['GB', 'DE', 'FR', 'CH', 'NL', 'SE', 'IT', 'ES'] : []
            })}
            className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
          >
            Europe
          </button>
          <button
            onClick={() => updateConfig({ 
              countries: countryMode === 'include' ? ['JP', 'AU', 'HK', 'SG'] : [],
              excludeCountries: countryMode === 'exclude' ? ['JP', 'AU', 'HK', 'SG'] : []
            })}
            className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
          >
            Asia Pacific
          </button>
        </div>

        {/* Countries by Region */}
        <div className="space-y-4">
          {Object.entries(countriesByRegion).map(([region, countries]) => (
            <div key={region}>
              <h4 className="text-sm font-medium text-gray-500 mb-2">{region}</h4>
              <div className="flex flex-wrap gap-2">
                {countries.map(country => {
                  const isSelected = countryMode === 'include'
                    ? config.countries.includes(country.code)
                    : config.excludeCountries.includes(country.code)
                  
                  return (
                    <button
                      key={country.code}
                      onClick={() => toggleCountry(country.code)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all ${
                        isSelected
                          ? countryMode === 'include'
                            ? 'border-green-500 bg-green-50 text-green-800'
                            : 'border-red-500 bg-red-50 text-red-800'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}
                    >
                      <span>{country.flag}</span>
                      <span className="text-sm">{country.name}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sector Filter */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Sector Filter</h3>
        <p className="text-sm text-gray-500 mb-4">
          Leave empty to include all sectors, or select specific sectors to focus on
        </p>
        <div className="flex flex-wrap gap-2">
          {SECTORS.map(sector => {
            const isSelected = config.sectors.includes(sector.id)
            return (
              <button
                key={sector.id}
                onClick={() => toggleSector(sector.id)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border transition-all ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50 text-blue-800'
                    : 'border-gray-200 hover:border-gray-300 bg-white'
                }`}
              >
                <span>{sector.icon}</span>
                <span className="text-sm">{sector.name}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Size & Liquidity Filters */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Min Market Cap
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
            <input
              type="number"
              value={config.minMarketCap || ''}
              onChange={(e) => updateConfig({ minMarketCap: Number(e.target.value) || undefined })}
              placeholder="e.g. 1000000000"
              className="w-full pl-7 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {config.minMarketCap && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500">
                {formatNumber(config.minMarketCap)}
              </span>
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Market Cap
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
            <input
              type="number"
              value={config.maxMarketCap || ''}
              onChange={(e) => updateConfig({ maxMarketCap: Number(e.target.value) || undefined })}
              placeholder="No limit"
              className="w-full pl-7 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {config.maxMarketCap && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500">
                {formatNumber(config.maxMarketCap)}
              </span>
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Min ADTV (20-day)
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
            <input
              type="number"
              value={config.minAdtv || ''}
              onChange={(e) => updateConfig({ minAdtv: Number(e.target.value) || undefined })}
              placeholder="e.g. 1000000"
              className="w-full pl-7 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {config.minAdtv && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500">
                {formatNumber(config.minAdtv)}
              </span>
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Min Free Float
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              max="100"
              value={config.minFreeFloat ? config.minFreeFloat * 100 : ''}
              onChange={(e) => updateConfig({ minFreeFloat: Number(e.target.value) / 100 || undefined })}
              placeholder="e.g. 10"
              className="w-full pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">%</span>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-blue-50 rounded-xl p-4">
        <h4 className="font-medium text-blue-900 mb-2">Universe Summary</h4>
        <div className="text-sm text-blue-800 space-y-1">
          <p>
            <strong>Asset Class:</strong> {config.assetClass || 'Not specified'}
          </p>
          <p>
            <strong>Countries:</strong>{' '}
            {config.countries.length > 0
              ? config.countries.map(c => COUNTRIES[c as keyof typeof COUNTRIES]?.name).join(', ')
              : config.excludeCountries.length > 0
                ? `All except ${config.excludeCountries.map(c => COUNTRIES[c as keyof typeof COUNTRIES]?.name).join(', ')}`
                : 'All countries'}
          </p>
          <p>
            <strong>Sectors:</strong>{' '}
            {config.sectors.length > 0
              ? config.sectors.map(s => SECTORS.find(sec => sec.id === s)?.name).join(', ')
              : 'All sectors'}
          </p>
          {config.minMarketCap && (
            <p><strong>Min Market Cap:</strong> ${formatNumber(config.minMarketCap)}</p>
          )}
          {config.minAdtv && (
            <p><strong>Min ADTV:</strong> ${formatNumber(config.minAdtv)}</p>
          )}
        </div>
      </div>
    </div>
  )
}



