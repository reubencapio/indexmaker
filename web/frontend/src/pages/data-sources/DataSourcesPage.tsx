import { useState } from 'react'
import { Database, Globe, Upload, Server, Plus } from 'lucide-react'
import { MarketDataProviderSettings } from '@/components/features/settings/MarketDataProviderSettings'
import { DataSourcesPage as CustomDataSourcesContent } from '@/pages/settings/DataSourcesPage'

type TabType = 'market-data' | 'custom-sources'

export function DataSourcesPage() {
  const [activeTab, setActiveTab] = useState<TabType>('market-data')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Database className="h-8 w-8 text-primary" />
          Data Sources
        </h1>
        <p className="text-muted-foreground mt-2">
          Configure where your market data comes from and manage custom data sources
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b">
        <nav className="flex gap-8" aria-label="Data source tabs">
          <button
            onClick={() => setActiveTab('market-data')}
            className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'market-data'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50'
            }`}
          >
            <Globe className="h-4 w-4" />
            Market Data Providers
          </button>
          <button
            onClick={() => setActiveTab('custom-sources')}
            className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'custom-sources'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50'
            }`}
          >
            <Server className="h-4 w-4" />
            Custom Data Sources
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="pt-2">
        {activeTab === 'market-data' && (
          <div className="space-y-6">
            {/* Info Banner */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6">
              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  <div className="h-12 w-12 bg-blue-100 rounded-xl flex items-center justify-center">
                    <Globe className="h-6 w-6 text-blue-600" />
                  </div>
                </div>
                <div>
                  <h3 className="font-semibold text-blue-900">Market Data Providers</h3>
                  <p className="text-blue-700 text-sm mt-1">
                    Choose where to source real-time prices, fundamentals, and market data. 
                    Your selection affects all indices and backtests.
                  </p>
                  <div className="flex gap-4 mt-3 text-xs text-blue-600">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      Yahoo Finance - Free, no setup
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                      OpenBB - Stock screening
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Market Data Provider Settings Component */}
            <div className="bg-card rounded-xl border p-6">
              <MarketDataProviderSettings />
            </div>
          </div>
        )}

        {activeTab === 'custom-sources' && (
          <div className="space-y-6">
            {/* Info Banner */}
            <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-6">
              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  <div className="h-12 w-12 bg-purple-100 rounded-xl flex items-center justify-center">
                    <Server className="h-6 w-6 text-purple-600" />
                  </div>
                </div>
                <div>
                  <h3 className="font-semibold text-purple-900">Custom Data Sources</h3>
                  <p className="text-purple-700 text-sm mt-1">
                    Connect your own securities database, import CSV files, or fetch from external APIs.
                    Perfect for proprietary data or private company lists.
                  </p>
                  <div className="flex gap-4 mt-3 text-xs text-purple-600">
                    <span className="flex items-center gap-1">
                      <Upload className="w-3 h-3" />
                      CSV Upload
                    </span>
                    <span className="flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      REST APIs
                    </span>
                    <span className="flex items-center gap-1">
                      <Database className="w-3 h-3" />
                      PostgreSQL / MySQL
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Custom Data Sources Content */}
            <CustomDataSourcesContent />
          </div>
        )}
      </div>
    </div>
  )
}



