import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { paymentsApi, getErrorMessage, type BillingInterval, type PlanPrice } from '@/lib/api'

export function usePlans() {
  return useQuery({
    queryKey: ['billing', 'plans'],
    queryFn: paymentsApi.plans,
    staleTime: 10 * 60 * 1000,
  })
}

export function useSubscription(enabled = true) {
  return useQuery({
    queryKey: ['billing', 'subscription'],
    queryFn: paymentsApi.subscription,
    enabled,
    staleTime: 60 * 1000,
  })
}

/** Redirects to Stripe Checkout or the customer portal, with loading and error state. */
export function useBillingActions() {
  const [pending, setPending] = useState<'checkout' | 'portal' | null>(null)

  const startCheckout = async (interval: BillingInterval) => {
    setPending('checkout')
    try {
      const { checkoutUrl } = await paymentsApi.createCheckoutSession(interval)
      window.location.href = checkoutUrl
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not start checkout. Please try again.'))
      setPending(null)
    }
  }

  const openPortal = async () => {
    setPending('portal')
    try {
      const { url } = await paymentsApi.createPortalSession()
      window.location.href = url
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not open billing. Please try again.'))
      setPending(null)
    }
  }

  return { startCheckout, openPortal, pending }
}

export function formatPrice(amountMinor: number, currency: string): string {
  const amount = amountMinor / 100
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency.toUpperCase(),
    // Whole amounts read better without ".00"; anything else keeps its cents.
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

/** Monthly-equivalent price, for comparing an annual plan against a monthly one. */
export function monthlyEquivalent(price: PlanPrice): number {
  return price.interval === 'year' ? price.unit_amount / 12 : price.unit_amount
}

/** Fraction saved by paying annually instead of monthly, or null if not comparable. */
export function annualSaving(prices: PlanPrice[]): number | null {
  const month = prices.find((p) => p.interval === 'month')
  const year = prices.find((p) => p.interval === 'year')
  if (!month || !year || month.currency !== year.currency || month.unit_amount <= 0) return null
  const saving = 1 - year.unit_amount / (month.unit_amount * 12)
  return saving > 0.005 ? saving : null
}
