import { describe, it, expect, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { PlanCards } from '../PlanCards'
import { UpgradeDialog } from '../UpgradeDialog'
import { UPGRADE_EVENT, getErrorMessage, type Plan, type PlansResponse } from '@/lib/api'

const plan = (id: Plan['id'], extra: Partial<Plan> = {}): Plan => ({
  id,
  name: id[0].toUpperCase() + id.slice(1),
  tagline: `${id} tagline`,
  max_indices: 3,
  max_data_sources: 2,
  max_public_shares: 1,
  max_embed_widgets: 1,
  analytics_history_years: 1,
  features: [],
  highlights: [`${id} highlight`],
  prices: [],
  ...extra,
})

const data: PlansResponse = {
  billing_enabled: true,
  trial_days: 0,
  plans: [
    plan('free'),
    plan('pro', {
      prices: [
        { id: 'price_m', interval: 'month', unit_amount: 1900, currency: 'usd' },
        { id: 'price_y', interval: 'year', unit_amount: 18000, currency: 'usd' },
      ],
    }),
    plan('enterprise'),
  ],
}

const renderCards = (props: Partial<Parameters<typeof PlanCards>[0]> = {}) =>
  render(
    <MemoryRouter>
      <PlanCards data={data} {...props} />
    </MemoryRouter>
  )

describe('PlanCards', () => {
  it('shows the annual price as a monthly equivalent by default, with the billed total', () => {
    renderCards()
    expect(screen.getByText('$15')).toBeInTheDocument()
    expect(screen.getByText('$180 billed annually')).toBeInTheDocument()
    expect(screen.getByText('Save 21%')).toBeInTheDocument()
  })

  it('checks out with the interval the user selected', async () => {
    const onUpgrade = vi.fn()
    renderCards({ currentTier: 'free', onUpgrade })
    await userEvent.click(screen.getByRole('tab', { name: /monthly/i }))
    expect(screen.getByText('$19')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Upgrade to Pro' }))
    expect(onUpgrade).toHaveBeenCalledWith('month')
  })

  it('sends signed-out visitors to registration rather than checkout', () => {
    renderCards()
    expect(screen.getByRole('link', { name: 'Get started' })).toHaveAttribute('href', '/register?plan=pro')
  })

  it('offers subscription management instead of a second purchase to Pro users', () => {
    renderCards({ currentTier: 'pro', onManage: vi.fn() })
    expect(screen.getByRole('button', { name: 'Manage subscription' })).toBeEnabled()
    expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument()
  })

  it('disables the upgrade button when checkout is not configured', () => {
    renderCards({ currentTier: 'free', onUpgrade: vi.fn(), data: { ...data, billing_enabled: false } })
    expect(screen.getByRole('button', { name: 'Unavailable right now' })).toBeDisabled()
  })

  it('advertises the trial when one is configured', () => {
    renderCards({ currentTier: 'free', onUpgrade: vi.fn(), data: { ...data, trial_days: 14 } })
    expect(screen.getByRole('button', { name: 'Start 14-day free trial' })).toBeInTheDocument()
  })
})

describe('UpgradeDialog', () => {
  it('opens with the server message when a plan limit is hit, and closes', async () => {
    render(
      <MemoryRouter>
        <UpgradeDialog />
      </MemoryRouter>
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    act(() => {
      window.dispatchEvent(
        new CustomEvent(UPGRADE_EVENT, {
          detail: {
            code: 'upgrade_required',
            message: 'Your Free plan includes 3 indices. Upgrade to add more.',
            feature: null,
            limit: 'max_indices',
            required_plan: 'pro',
          },
        })
      )
    })

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Your Free plan includes 3 indices. Upgrade to add more.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Not now' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('getErrorMessage', () => {
  const error = (detail: unknown) => ({ response: { data: { detail } } })

  it('reads string, structured and validation-list details', () => {
    expect(getErrorMessage(error('Plain message'))).toBe('Plain message')
    expect(getErrorMessage(error({ code: 'upgrade_required', message: 'Upgrade needed' }))).toBe('Upgrade needed')
    expect(getErrorMessage(error([{ msg: 'Field required' }]))).toBe('Field required')
  })

  it('falls back when there is nothing usable', () => {
    expect(getErrorMessage(new Error('Network Error'), 'Fallback')).toBe('Fallback')
  })
})
