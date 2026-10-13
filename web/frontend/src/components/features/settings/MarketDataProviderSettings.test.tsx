import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MarketDataProviderSettings } from './MarketDataProviderSettings'
import { marketDataProvidersApi } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  marketDataProvidersApi: {
    list: vi.fn(),
    setActive: vi.fn(),
    test: vi.fn(),
    removeKey: vi.fn(),
  },
  getErrorMessage: (_error: unknown, fallback: string) => fallback,
}))

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

const source = (overrides: Record<string, unknown>) => ({
  description: 'A source.',
  features: [],
  limitations: [],
  requires_api_key: false,
  is_available: true,
  has_api_key: false,
  ...overrides,
})

function renderSettings(sources: Record<string, unknown>[]) {
  vi.mocked(marketDataProvidersApi.list).mockResolvedValue({
    sources,
    active_source: 'yahoo',
  } as never)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MarketDataProviderSettings />
    </QueryClientProvider>
  )
}

const yahoo = source({ id: 'yahoo', name: 'Yahoo Finance' })
const fmp = (overrides = {}) =>
  source({
    id: 'fmp',
    name: 'Financial Modeling Prep',
    requires_api_key: true,
    key_url: 'https://example.com/key',
    ...overrides,
  })

describe('MarketDataProviderSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(marketDataProvidersApi.setActive).mockResolvedValue({
      source_id: 'fmp',
      is_connected: true,
      message: 'ok',
    })
  })

  it('does not switch to a keyed source until a key is entered', async () => {
    renderSettings([yahoo, fmp()])
    await userEvent.click(await screen.findByRole('button', { name: 'Use This' }))

    expect(marketDataProvidersApi.setActive).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: /Get a free key/ })).toHaveAttribute(
      'href',
      'https://example.com/key'
    )
  })

  it('sends the entered key, then clears it from the page', async () => {
    renderSettings([yahoo, fmp()])
    const input = await screen.findByLabelText(/API Key/)
    await userEvent.type(input, 'my-key')
    await userEvent.click(screen.getByRole('button', { name: 'Use This' }))

    await waitFor(() =>
      expect(marketDataProvidersApi.setActive).toHaveBeenCalledWith('fmp', 'my-key')
    )
    await waitFor(() => expect(input).toHaveValue(''))
  })

  it('reuses a saved key without asking for it again, and can remove it', async () => {
    vi.mocked(marketDataProvidersApi.removeKey).mockResolvedValue(fmp() as never)
    renderSettings([yahoo, fmp({ has_api_key: true })])

    await userEvent.click(await screen.findByRole('button', { name: 'Use This' }))
    await waitFor(() =>
      expect(marketDataProvidersApi.setActive).toHaveBeenCalledWith('fmp', undefined)
    )

    await userEvent.click(screen.getByRole('button', { name: 'Remove saved key' }))
    await waitFor(() => expect(marketDataProvidersApi.removeKey).toHaveBeenCalledWith('fmp'))
  })
})
