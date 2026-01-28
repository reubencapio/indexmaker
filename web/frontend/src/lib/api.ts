import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

// Determine API URL with bulletproof production detection
function getApiUrl(): string {
  // If explicitly set via env, use it
  const envUrl = import.meta.env.VITE_API_URL
  if (envUrl) {
    return envUrl
  }

  // Auto-detect based on current hostname
  const hostname = window.location.hostname

  // Production domains
  if (hostname === 'indexmaker.ai' || hostname === 'www.indexmaker.ai') {
    return 'https://api.indexmaker.ai'
  }
  if (hostname === 'indexforge.ai' || hostname === 'www.indexforge.ai') {
    return 'https://api.indexforge.ai'
  }
  // Vercel preview deployments
  if (hostname.includes('vercel.app')) {
    return 'https://api.indexmaker.ai'
  }

  // Local development
  return 'http://localhost:8000'
}

const API_URL = getApiUrl()

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) {
          throw new Error('No refresh token')
        }

        const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        })

        const { access_token, refresh_token } = response.data
        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)

        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        // Clear tokens and redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    return response.data
  },
  register: async (email: string, password: string, fullName?: string) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    return response.data
  },
  me: async () => {
    const response = await api.get('/auth/me')
    return response.data
  },
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}

// Support API
export const supportApi = {
  contact: async (data: { name: string; email: string; subject: string; message: string }) => {
    const response = await api.post('/support/contact', data)
    return response.data
  },
}

// Indices API
export const indicesApi = {
  list: async (params?: { skip?: number; limit?: number; status?: string }) => {
    const response = await api.get('/indices', { params })
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/indices/${id}`)
    return response.data
  },
  create: async (data: CreateIndexRequest) => {
    const response = await api.post('/indices', data)
    return response.data
  },
  update: async (id: string, data: UpdateIndexRequest) => {
    const response = await api.patch(`/indices/${id}`, data)
    return response.data
  },
  delete: async (id: string) => {
    await api.delete(`/indices/${id}`)
  },
  addComponent: async (indexId: string, ticker: string, weight: number) => {
    const response = await api.post(`/indices/${indexId}/components`, {
      ticker,
      weight,
    })
    return response.data
  },
  removeComponent: async (indexId: string, ticker: string) => {
    await api.delete(`/indices/${indexId}/components/${ticker}`)
  },
  calculate: async (id: string) => {
    const response = await api.post(`/indices/${id}/calculate`)
    return response.data
  },
  rebalance: async (id: string) => {
    const response = await api.post(`/indices/${id}/rebalance`)
    return response.data
  },
  getAnalytics: async (id: string, period?: string) => {
    const response = await api.get(`/indices/${id}/analytics`, { params: { period } })
    return response.data
  },
}

// Backtests API
export const backtestsApi = {
  list: async (indexId?: string) => {
    const response = await api.get('/backtests', { params: { index_id: indexId } })
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/backtests/${id}`)
    return response.data
  },
  create: async (indexId: string, data: CreateBacktestRequest) => {
    const response = await api.post('/backtests', data, {
      params: { index_id: indexId },
    })
    return response.data
  },
  delete: async (id: string) => {
    await api.delete(`/backtests/${id}`)
  },
  status: async (id: string) => {
    const response = await api.get(`/backtests/${id}/status`)
    return response.data
  },
}

// Market Data API
export const marketDataApi = {
  quote: async (ticker: string) => {
    const response = await api.get(`/market-data/quote/${ticker}`)
    return response.data
  },
  quotes: async (tickers: string[]) => {
    const response = await api.get('/market-data/quotes', {
      params: { tickers: tickers.join(',') },
    })
    return response.data
  },
  search: async (query: string) => {
    const response = await api.get('/market-data/search', { params: { query } })
    return response.data
  },
  sectors: async () => {
    const response = await api.get('/market-data/sectors')
    return response.data
  },
  countries: async () => {
    const response = await api.get('/market-data/countries')
    return response.data
  },
}

// Types
export interface CreateIndexRequest {
  name: string
  identifier: string
  description?: string
  currency?: string
  weighting_method?: string
  rebalance_frequency?: string
  base_date: string
  base_value?: number
  min_market_cap?: number
  max_components?: number
  countries?: string[]
  sectors?: string[]
  max_weight?: number
  custom_rules?: Record<string, any>
  components?: Array<{ ticker: string; weight: number }>
}

export interface UpdateIndexRequest {
  name?: string
  description?: string
  weighting_method?: string
  rebalance_frequency?: string
  status?: string
  is_public?: boolean
  custom_rules?: Record<string, any>
}

export interface CreateBacktestRequest {
  name: string
  start_date: string
  end_date: string
  initial_value?: number
  benchmark_ticker?: string
}

// Data Sources API
export const dataSourcesApi = {
  list: async () => {
    const response = await api.get('/data-sources')
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/data-sources/${id}`)
    return response.data
  },
  create: async (data: CreateDataSourceRequest) => {
    const response = await api.post('/data-sources', data)
    return response.data
  },
  update: async (id: string, data: Partial<CreateDataSourceRequest>) => {
    const response = await api.patch(`/data-sources/${id}`, data)
    return response.data
  },
  delete: async (id: string) => {
    await api.delete(`/data-sources/${id}`)
  },
  addSecurities: async (id: string, securities: SecurityData[]) => {
    const response = await api.post(`/data-sources/${id}/securities`, { securities })
    return response.data
  },
  listSecurities: async (id: string, params?: { skip?: number; limit?: number; search?: string }) => {
    const response = await api.get(`/data-sources/${id}/securities`, { params })
    return response.data
  },
  removeSecurity: async (id: string, ticker: string) => {
    await api.delete(`/data-sources/${id}/securities/${ticker}`)
  },
  importCSV: async (id: string, file: File, mapping: CSVColumnMapping) => {
    const formData = new FormData()
    formData.append('file', file)
    const params = new URLSearchParams()
    if (mapping.ticker_column) params.append('ticker_column', mapping.ticker_column)
    if (mapping.name_column) params.append('name_column', mapping.name_column)
    if (mapping.sector_column) params.append('sector_column', mapping.sector_column)
    if (mapping.country_column) params.append('country_column', mapping.country_column)
    if (mapping.market_cap_column) params.append('market_cap_column', mapping.market_cap_column)
    if (mapping.price_column) params.append('price_column', mapping.price_column)

    const response = await api.post(`/data-sources/${id}/import-csv?${params.toString()}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },
  syncFromAPI: async (id: string) => {
    const response = await api.post(`/data-sources/${id}/sync-api`)
    return response.data
  },
  syncFromDatabase: async (id: string) => {
    const response = await api.post(`/data-sources/${id}/sync-database`)
    return response.data
  },
  testAPIConnection: async (config: APIConfig) => {
    const response = await api.post('/data-sources/test-api-connection', config)
    return response.data
  },
  testDatabaseConnection: async (config: Omit<DatabaseConfig, 'query'>) => {
    const response = await api.post('/data-sources/test-database-connection', config)
    return response.data
  },
}

// Market Data Providers API (Yahoo, OpenBB, etc.)
export const marketDataProvidersApi = {
  list: async (): Promise<MarketDataSourceListResponse> => {
    const response = await api.get('/market-data-providers/')
    return response.data
  },
  getActive: async (): Promise<MarketDataSource> => {
    const response = await api.get('/market-data-providers/active')
    return response.data
  },
  setActive: async (sourceId: string, apiKey?: string): Promise<MarketDataSourceStatus> => {
    const response = await api.post('/market-data-providers/active', {
      source_id: sourceId,
      api_key: apiKey,
    })
    return response.data
  },
  test: async (sourceId: string, apiKey?: string): Promise<MarketDataSourceStatus> => {
    const params = apiKey ? `?api_key=${apiKey}` : ''
    const response = await api.get(`/market-data-providers/${sourceId}/test${params}`)
    return response.data
  },
}

export interface CreateDataSourceRequest {
  name: string
  description?: string
  source_type?: string
  config?: Record<string, any>
  field_mapping?: Record<string, string>
}

export interface SecurityData {
  ticker: string
  name?: string
  sector?: string
  industry?: string
  country?: string
  exchange?: string
  market_cap?: number
  price?: number
  avg_volume?: number
  free_float?: number
  custom_fields?: Record<string, any>
}

export interface CSVColumnMapping {
  ticker_column: string
  name_column?: string
  sector_column?: string
  country_column?: string
  market_cap_column?: string
  price_column?: string
}

export interface APIConfig {
  endpoint: string
  method?: 'GET' | 'POST'
  headers?: Record<string, string>
  params?: Record<string, string>
  body?: Record<string, any>
  response_path?: string
}

export interface DatabaseConfig {
  db_type: 'postgresql' | 'mysql'
  host: string
  port?: number
  database: string
  username: string
  password: string
  query: string
}

export interface FieldMapping {
  ticker: string
  name?: string
  sector?: string
  industry?: string
  country?: string
  market_cap?: string
  price?: string
  [key: string]: string | undefined
}

// Corporate Actions API
export const corporateActionsApi = {
  list: async (params?: { ticker?: string; action_type?: string; status?: string }) => {
    const response = await api.get('/corporate-actions', { params })
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/corporate-actions/${id}`)
    return response.data
  },
  create: async (data: CreateCorporateActionRequest) => {
    const response = await api.post('/corporate-actions', data)
    return response.data
  },
  apply: async (actionId: string, indexId: string, applyToHistory?: boolean) => {
    const response = await api.post(`/corporate-actions/${actionId}/apply/${indexId}`, null, {
      params: { apply_to_history: applyToHistory },
    })
    return response.data
  },
  getPendingForIndex: async (indexId: string) => {
    const response = await api.get(`/corporate-actions/pending/for-index/${indexId}`)
    return response.data
  },
}

export interface CreateCorporateActionRequest {
  ticker: string
  action_type: 'stock_split' | 'reverse_split' | 'cash_dividend' | 'stock_dividend' | 'merger' | 'acquisition' | 'spin_off' | 'delisting' | 'ticker_change' | 'name_change'
  effective_date: string
  ratio?: number
  dividend_amount?: number
  dividend_currency?: string
  new_ticker?: string
  new_name?: string
  description?: string
}

// Delivery API (Webhooks, SFTP, Email)
export const deliveryApi = {
  // Webhooks
  listWebhooks: async () => {
    const response = await api.get('/delivery/webhooks')
    return response.data
  },
  createWebhook: async (data: CreateWebhookRequest) => {
    const response = await api.post('/delivery/webhooks', data)
    return response.data
  },
  getWebhook: async (id: string) => {
    const response = await api.get(`/delivery/webhooks/${id}`)
    return response.data
  },
  updateWebhook: async (id: string, data: Partial<CreateWebhookRequest>) => {
    const response = await api.patch(`/delivery/webhooks/${id}`, data)
    return response.data
  },
  deleteWebhook: async (id: string) => {
    await api.delete(`/delivery/webhooks/${id}`)
  },
  testWebhook: async (id: string) => {
    const response = await api.post(`/delivery/webhooks/${id}/test`)
    return response.data
  },

  // SFTP
  listSFTP: async () => {
    const response = await api.get('/delivery/sftp')
    return response.data
  },
  createSFTP: async (data: CreateSFTPRequest) => {
    const response = await api.post('/delivery/sftp', data)
    return response.data
  },
  getSFTP: async (id: string) => {
    const response = await api.get(`/delivery/sftp/${id}`)
    return response.data
  },
  updateSFTP: async (id: string, data: Partial<CreateSFTPRequest>) => {
    const response = await api.patch(`/delivery/sftp/${id}`, data)
    return response.data
  },
  deleteSFTP: async (id: string) => {
    await api.delete(`/delivery/sftp/${id}`)
  },
  testSFTP: async (id: string) => {
    const response = await api.post(`/delivery/sftp/${id}/test`)
    return response.data
  },

  // Email
  listEmail: async () => {
    const response = await api.get('/delivery/email')
    return response.data
  },
  createEmail: async (data: CreateEmailSubscriptionRequest) => {
    const response = await api.post('/delivery/email', data)
    return response.data
  },
  getEmail: async (id: string) => {
    const response = await api.get(`/delivery/email/${id}`)
    return response.data
  },
  updateEmail: async (id: string, data: Partial<CreateEmailSubscriptionRequest>) => {
    const response = await api.patch(`/delivery/email/${id}`, data)
    return response.data
  },
  deleteEmail: async (id: string) => {
    await api.delete(`/delivery/email/${id}`)
  },

  // Logs
  getLogs: async (params?: { delivery_type?: string; limit?: number }) => {
    const response = await api.get('/delivery/logs', { params })
    return response.data
  },
}

export interface CreateWebhookRequest {
  name: string
  url: string
  secret_key?: string
  headers?: Record<string, string>
  events?: string[]
  index_ids?: string[]
  max_retries?: number
}

export interface CreateSFTPRequest {
  name: string
  host: string
  port?: number
  username: string
  password?: string
  private_key?: string
  remote_path?: string
  frequency?: string
  schedule_time?: string
  index_ids?: string[]
  file_format?: string
}

export interface CreateEmailSubscriptionRequest {
  name: string
  recipients: string[]
  frequency?: string
  schedule_time?: string
  index_ids?: string[]
  report_type?: string
  include_attachments?: boolean
}

// Embeds & Shares API
export const embedsApi = {
  // Public Shares
  listShares: async () => {
    const response = await api.get('/embeds/shares')
    return response.data
  },
  createShare: async (data: CreatePublicShareRequest) => {
    const response = await api.post('/embeds/shares', data)
    return response.data
  },
  getShare: async (id: string) => {
    const response = await api.get(`/embeds/shares/${id}`)
    return response.data
  },
  updateShare: async (id: string, data: Partial<CreatePublicShareRequest>) => {
    const response = await api.patch(`/embeds/shares/${id}`, data)
    return response.data
  },
  deleteShare: async (id: string) => {
    await api.delete(`/embeds/shares/${id}`)
  },

  // Embed Widgets
  listWidgets: async () => {
    const response = await api.get('/embeds/widgets')
    return response.data
  },
  createWidget: async (data: CreateEmbedWidgetRequest) => {
    const response = await api.post('/embeds/widgets', data)
    return response.data
  },
  getWidget: async (id: string) => {
    const response = await api.get(`/embeds/widgets/${id}`)
    return response.data
  },
  updateWidget: async (id: string, data: Partial<CreateEmbedWidgetRequest>) => {
    const response = await api.patch(`/embeds/widgets/${id}`, data)
    return response.data
  },
  deleteWidget: async (id: string) => {
    await api.delete(`/embeds/widgets/${id}`)
  },
  regenerateToken: async (id: string) => {
    const response = await api.post(`/embeds/widgets/${id}/regenerate-token`)
    return response.data
  },
}

export interface CreatePublicShareRequest {
  index_id: string
  slug?: string
  show_chart?: boolean
  show_components?: boolean
  show_performance?: boolean
  show_factsheet?: boolean
  allow_download?: boolean
  title_override?: string
  description_override?: string
  theme?: 'light' | 'dark' | 'auto'
  password?: string
  expires_at?: string
  allowed_domains?: string[]
}

export interface CreateEmbedWidgetRequest {
  index_id: string
  name: string
  widget_type?: 'chart' | 'table' | 'factsheet' | 'performance' | 'components'
  width?: string
  height?: string
  theme?: 'light' | 'dark' | 'auto'
  primary_color?: string
  background_color?: string
  chart_type?: 'line' | 'area' | 'candlestick'
  show_volume?: boolean
  show_legend?: boolean
  default_period?: '1M' | '3M' | '6M' | '1Y' | '5Y' | 'ALL'
  allowed_domains?: string[]
}

// Reports API
export const reportsApi = {
  // Templates
  listTemplates: async (includeSystem?: boolean) => {
    const response = await api.get('/reports/templates', { params: { include_system: includeSystem } })
    return response.data
  },
  createTemplate: async (data: CreateReportTemplateRequest) => {
    const response = await api.post('/reports/templates', data)
    return response.data
  },
  getTemplate: async (id: string) => {
    const response = await api.get(`/reports/templates/${id}`)
    return response.data
  },
  updateTemplate: async (id: string, data: Partial<CreateReportTemplateRequest>) => {
    const response = await api.patch(`/reports/templates/${id}`, data)
    return response.data
  },
  deleteTemplate: async (id: string) => {
    await api.delete(`/reports/templates/${id}`)
  },

  // Generated Reports
  list: async (params?: { index_id?: string; limit?: number }) => {
    const response = await api.get('/reports', { params })
    return response.data
  },
  generate: async (data: GenerateReportRequest) => {
    const response = await api.post('/reports/generate', data)
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/reports/${id}`)
    return response.data
  },
  download: async (id: string) => {
    const response = await api.get(`/reports/${id}/download`, { responseType: 'blob' })
    return response.data
  },
  delete: async (id: string) => {
    await api.delete(`/reports/${id}`)
  },

  // Quick factsheet
  quickFactsheet: async (indexId: string, format?: 'html' | 'json') => {
    const response = await api.get(`/reports/quick/${indexId}`, {
      params: { format },
      responseType: format === 'html' ? 'blob' : 'json',
    })
    return response.data
  },
}

export interface CreateReportTemplateRequest {
  name: string
  description?: string
  report_type?: string
  show_logo?: boolean
  logo_url?: string
  header_text?: string
  footer_text?: string
  sections?: Record<string, boolean>
  primary_color?: string
  secondary_color?: string
  font_family?: string
}

export interface GenerateReportRequest {
  index_id: string
  template_id?: string
  report_type?: string
  report_format?: 'pdf' | 'html' | 'xlsx'
  as_of_date?: string
  period_start?: string
  period_end?: string
  is_public?: boolean
}

// AI Index Creation API
export const aiApi = {
  status: async () => {
    const response = await api.get('/ai/status')
    return response.data
  },
  generate: async (data: AIGenerateRequest) => {
    const response = await api.post('/ai/generate', data)
    return response.data
  },
  create: async (data: AIGenerateRequest) => {
    const response = await api.post('/ai/create', data)
    return response.data
  },
}

export interface AIGenerateRequest {
  description: string
  base_date?: string
  base_value?: number
}

export interface AIGenerateResponse {
  index: {
    name: string
    identifier: string
    description: string
    currency: string
    base_date: string
    base_value: number
    countries: string[]
    sectors: string[]
    tickers: string[]
    theme_keywords?: string[]
    min_market_cap?: number
    max_components: number
    weighting_method: string
    max_weight?: number
    rebalance_frequency: string
    custom_rules?: {
      min_dividend_yield?: number | null
      min_esg_score?: number | null
    }
  }
  explanation: string
  config: Record<string, any>
}

// Data Sources API
// Market Data Provider types (Yahoo, OpenBB, etc.)
export interface MarketDataSource {
  id: string
  name: string
  description: string
  features: string[]
  limitations: string[]
  requires_api_key: boolean
  is_available: boolean
  logo?: string
}

export interface MarketDataSourceListResponse {
  sources: MarketDataSource[]
  active_source: string
}

export interface MarketDataSourceStatus {
  source_id: string
  is_connected: boolean
  message: string
}
