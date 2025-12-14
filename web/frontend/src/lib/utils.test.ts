import { describe, it, expect } from 'vitest'
import { cn, formatCurrency, formatPercent, formatDate, formatMarketCap } from './utils'

describe('cn (className merge utility)', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('handles conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz')
    expect(cn('foo', true && 'bar', 'baz')).toBe('foo bar baz')
  })

  it('handles undefined and null', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar')
  })

  it('merges tailwind classes correctly', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4')
  })
})

describe('formatCurrency', () => {
  it('formats USD currency', () => {
    expect(formatCurrency(1234.56)).toBe('$1,234.56')
  })

  it('formats large numbers', () => {
    expect(formatCurrency(1000000)).toBe('$1,000,000.00')
  })

  it('formats zero', () => {
    expect(formatCurrency(0)).toBe('$0.00')
  })

  it('formats negative numbers', () => {
    expect(formatCurrency(-500)).toBe('-$500.00')
  })
})

describe('formatPercent', () => {
  it('formats percentages', () => {
    expect(formatPercent(0.1234)).toBe('12.34%')
  })

  it('formats small percentages', () => {
    expect(formatPercent(0.001)).toBe('0.10%')
  })

  it('formats zero', () => {
    expect(formatPercent(0)).toBe('0.00%')
  })

  it('formats negative percentages', () => {
    expect(formatPercent(-0.05)).toBe('-5.00%')
  })
})

describe('formatMarketCap', () => {
  it('formats billions', () => {
    expect(formatMarketCap(1500000000000)).toBe('$1.50T')
  })

  it('formats millions', () => {
    expect(formatMarketCap(500000000)).toBe('$500.00M')
  })

  it('formats thousands', () => {
    expect(formatMarketCap(50000)).toBe('$50.00K')
  })

  it('formats small numbers', () => {
    expect(formatMarketCap(500)).toBe('$500.00')
  })
})

describe('formatDate', () => {
  it('formats date string', () => {
    const result = formatDate('2024-01-15')
    expect(result).toContain('2024')
  })

  it('formats Date object', () => {
    const date = new Date('2024-06-20')
    const result = formatDate(date)
    expect(result).toContain('2024')
  })
})

