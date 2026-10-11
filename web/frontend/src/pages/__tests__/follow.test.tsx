import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { FollowActionPage } from '../FollowActionPage'
import { LegalPage } from '../LegalPage'
import { publicApi } from '@/lib/api'

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    publicApi: { ...actual.publicApi, confirmFollow: vi.fn(), unsubscribeFollow: vi.fn() },
  }
})

const renderAt = (path: string) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/follow/confirm/:token" element={<FollowActionPage action="confirm" />} />
          <Route path="/follow/unsubscribe/:token" element={<FollowActionPage action="unsubscribe" />} />
          <Route path="/terms" element={<LegalPage document="terms" />} />
          <Route path="/refunds" element={<LegalPage document="refunds" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )

describe('FollowActionPage', () => {
  beforeEach(() => {
    vi.mocked(publicApi.confirmFollow).mockReset()
    vi.mocked(publicApi.unsubscribeFollow).mockReset()
  })

  it('confirms on arrival', async () => {
    vi.mocked(publicApi.confirmFollow).mockResolvedValue({ title: 'Dividend Leaders', slug: 'div' })

    renderAt('/follow/confirm/tok123')

    expect(await screen.findByText("You're following Dividend Leaders")).toBeInTheDocument()
    expect(publicApi.confirmFollow).toHaveBeenCalledWith('tok123')
    expect(screen.getByRole('link', { name: 'View the index' })).toHaveAttribute('href', '/public/div')
  })

  it('explains an invalid confirmation link', async () => {
    vi.mocked(publicApi.confirmFollow).mockRejectedValue(new Error('404'))

    renderAt('/follow/confirm/bad')

    expect(await screen.findByText("This link isn't valid")).toBeInTheDocument()
  })

  it('does not unsubscribe until the button is pressed', async () => {
    vi.mocked(publicApi.unsubscribeFollow).mockResolvedValue({ title: 'Dividend Leaders', slug: 'div' })

    renderAt('/follow/unsubscribe/tok123')

    expect(screen.getByText('Stop following this index?')).toBeInTheDocument()
    expect(publicApi.unsubscribeFollow).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Unsubscribe' }))

    await waitFor(() => expect(publicApi.unsubscribeFollow).toHaveBeenCalledWith('tok123'))
    expect(await screen.findByText("You've unfollowed Dividend Leaders")).toBeInTheDocument()
  })
})

describe('LegalPage', () => {
  it('shows the requested document', () => {
    renderAt('/terms')
    expect(screen.getByRole('heading', { level: 1, name: 'Terms of Service' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Not investment advice' })).toBeInTheDocument()
  })

  it('states the refund window', () => {
    renderAt('/refunds')
    expect(screen.getByText(/within 14 days of your first payment/)).toBeInTheDocument()
  })
})
