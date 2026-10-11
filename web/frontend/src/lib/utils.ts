import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value)
}

export function formatPercent(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatDate(date: string | Date): string {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/** The symbol for an ISO currency code, e.g. "€" for EUR; the code itself if unknown. */
export function currencySymbol(currency: string = 'USD'): string {
  try {
    const parts = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      currencyDisplay: 'narrowSymbol',
    }).formatToParts(0)
    return parts.find((part) => part.type === 'currency')?.value ?? currency
  } catch {
    return `${currency} `
  }
}

/**
 * A market cap in short form, in the given currency.
 *
 * The currency matters: amounts are stored in the index currency, and showing a
 * euro or krona figure behind a dollar sign misstates it.
 */
export function formatMarketCap(value: number, currency: string = 'USD'): string {
  const symbol = currencySymbol(currency)
  if (value >= 1e12) return `${symbol}${(value / 1e12).toFixed(2)}T`
  if (value >= 1e9) return `${symbol}${(value / 1e9).toFixed(2)}B`
  if (value >= 1e6) return `${symbol}${(value / 1e6).toFixed(2)}M`
  if (value >= 1e3) return `${symbol}${(value / 1e3).toFixed(2)}K`
  return `${symbol}${value.toFixed(2)}`
}
