import { describe, it, expect } from 'vitest'
import { annualSaving, formatPrice, monthlyEquivalent } from './useBilling'
import type { PlanPrice } from '@/lib/api'

const month: PlanPrice = { id: 'm', interval: 'month', unit_amount: 1900, currency: 'usd' }
const year: PlanPrice = { id: 'y', interval: 'year', unit_amount: 18000, currency: 'usd' }

describe('billing helpers', () => {
  it('formats whole amounts without cents and others with them', () => {
    expect(formatPrice(1900, 'usd')).toBe('$19')
    expect(formatPrice(1999, 'usd')).toBe('$19.99')
  })

  it('converts an annual price to its monthly equivalent', () => {
    expect(monthlyEquivalent(year)).toBe(1500)
    expect(monthlyEquivalent(month)).toBe(1900)
  })

  it('reports the annual saving against twelve monthly payments', () => {
    // 180 a year against 19 * 12 = 228.
    expect(annualSaving([month, year])).toBeCloseTo(1 - 180 / 228)
  })

  it('reports no saving when only one interval exists or annual is not cheaper', () => {
    expect(annualSaving([year])).toBeNull()
    expect(annualSaving([month, { ...year, unit_amount: 22800 }])).toBeNull()
    expect(annualSaving([month, { ...year, currency: 'eur' }])).toBeNull()
  })
})
