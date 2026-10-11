import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReproduceCard, summariseExclusions } from './ReproduceCard'
import { indicesApi } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  indicesApi: {
    downloadSpec: vi.fn().mockResolvedValue(undefined),
    downloadBuildData: vi.fn().mockResolvedValue(undefined),
    rebuild: vi.fn().mockResolvedValue({}),
  },
  getErrorMessage: (_error: unknown, fallback: string) => fallback,
}))

const buildInfo = {
  as_of: '2026-10-11',
  data_source: 'Yahoo Finance',
  candidates: 589,
  exclusions: {
    'NVD.DE': 'country United States is not in the universe',
    'APC.DE': 'country United States is not in the universe',
    'TINY.DE': 'market cap is below the minimum',
  },
}

function renderCard(props: Partial<Parameters<typeof ReproduceCard>[0]> = {}) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ReproduceCard
        indexId="idx-1"
        identifier="EUQUANTUM"
        buildInfo={buildInfo}
        screened
        {...props}
      />
    </QueryClientProvider>
  )
}

describe('summariseExclusions', () => {
  it('counts candidates per reason, most common first', () => {
    expect(summariseExclusions(buildInfo.exclusions)).toEqual([
      { reason: 'country United States is not in the universe', count: 2 },
      { reason: 'market cap is below the minimum', count: 1 },
    ])
  })

  it('handles a build with nothing left out', () => {
    expect(summariseExclusions(undefined)).toEqual([])
  })
})

describe('ReproduceCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows when, from what data and from how many companies the index was built', () => {
    renderCard()
    expect(screen.getByText('2026-10-11')).toBeInTheDocument()
    expect(screen.getByText('Yahoo Finance')).toBeInTheDocument()
    expect(screen.getByText('589')).toBeInTheDocument()
    expect(screen.getByText('3 left out, by reason')).toBeInTheDocument()
    expect(screen.getByText('country United States is not in the universe')).toBeInTheDocument()
  })

  it('says who chose the members', () => {
    renderCard()
    expect(screen.getByText(/The rules chose the members/)).toBeInTheDocument()
  })

  it('describes an index built from named companies differently', () => {
    renderCard({ screened: false })
    expect(screen.getByText(/companies named in the rules/)).toBeInTheDocument()
  })

  it('gives the command that reproduces the index from the two files', () => {
    renderCard()
    expect(
      screen.getByText(/indexforge build euquantum\.yaml --data euquantum\.data\.json/)
    ).toBeInTheDocument()
  })

  it('downloads the rules and the market data', async () => {
    const user = userEvent.setup()
    renderCard()

    await user.click(screen.getByRole('button', { name: /Rules \(euquantum\.yaml\)/ }))
    await waitFor(() =>
      expect(indicesApi.downloadSpec).toHaveBeenCalledWith('idx-1', 'EUQUANTUM')
    )

    await user.click(screen.getByRole('button', { name: /Market data/ }))
    await waitFor(() =>
      expect(indicesApi.downloadBuildData).toHaveBeenCalledWith('idx-1', 'EUQUANTUM')
    )
  })

  it('rebuilds on request', async () => {
    const user = userEvent.setup()
    renderCard()
    await user.click(screen.getByRole('button', { name: /Rebuild with today/ }))
    await waitFor(() => expect(indicesApi.rebuild).toHaveBeenCalledWith('idx-1'))
  })

  it('warns when a market cap could not be converted', () => {
    renderCard({ buildInfo: { ...buildInfo, unconverted: { 'ERIC-B.ST': 'SEK' } } })
    expect(screen.getByText(/No exchange rate was available for ERIC-B\.ST/)).toBeInTheDocument()
  })

  it('renders without build details for an index that has only a spec', () => {
    renderCard({ buildInfo: null })
    expect(screen.getByText('How this index was built')).toBeInTheDocument()
    expect(screen.queryByText('Built as of')).not.toBeInTheDocument()
  })
})
