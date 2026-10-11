import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { BillingInterval, Plan, PlansResponse } from '@/lib/api'
import { annualSaving, formatPrice, monthlyEquivalent } from '@/hooks/useBilling'

interface PlanCardsProps {
  data: PlansResponse
  /** The signed-in user's tier. Omit on public pages. */
  currentTier?: Plan['id']
  /** Called when a signed-in free user picks Pro. Omit on public pages. */
  onUpgrade?: (interval: BillingInterval) => void
  /** Called when a paying user wants to change or cancel. */
  onManage?: () => void
  busy?: boolean
}

/**
 * Plan comparison shared by the landing page and the in-app pricing page.
 * Names, limits, feature bullets and prices all come from the API, so this
 * never states something the backend does not enforce or Stripe does not charge.
 */
export function PlanCards({ data, currentTier, onUpgrade, onManage, busy }: PlanCardsProps) {
  const pro = data.plans.find((p) => p.id === 'pro')
  const prices = pro?.prices ?? []
  const hasBoth = prices.length > 1
  const [billingInterval, setBillingInterval] = useState<BillingInterval>(
    prices.some((p) => p.interval === 'year') ? 'year' : 'month'
  )
  const saving = annualSaving(prices)
  const selected = prices.find((p) => p.interval === billingInterval) ?? prices[0]

  return (
    <div className="space-y-8">
      {hasBoth && (
        <div className="flex justify-center">
          <div className="inline-flex items-center rounded-full border bg-muted p-1" role="tablist" aria-label="Billing period">
            {(['month', 'year'] as const).map((option) => (
              <button
                key={option}
                role="tab"
                aria-selected={billingInterval === option}
                onClick={() => setBillingInterval(option)}
                className={cn(
                  'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
                  billingInterval === option ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {option === 'month' ? 'Monthly' : 'Annual'}
                {option === 'year' && saving && (
                  <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                    Save {Math.round(saving * 100)}%
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        {data.plans.map((plan) => {
          const isCurrent = plan.id === currentTier
          const isPro = plan.id === 'pro'

          return (
            <div
              key={plan.id}
              className={cn(
                'relative flex flex-col rounded-xl border bg-card p-6',
                isPro && 'border-blue-600 shadow-lg ring-1 ring-blue-600'
              )}
            >
              {isPro && (
                <span className="absolute -top-3 left-6 rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold text-white">
                  {isCurrent ? 'Your plan' : 'Most popular'}
                </span>
              )}
              {!isPro && isCurrent && (
                <span className="absolute -top-3 left-6 rounded-full bg-foreground px-3 py-1 text-xs font-semibold text-background">
                  Your plan
                </span>
              )}

              <h3 className="text-xl font-bold">{plan.name}</h3>
              <p className="mt-1 min-h-[2.5rem] text-sm text-muted-foreground">{plan.tagline}</p>

              <div className="mt-4 min-h-[4.5rem]">
                {plan.id === 'free' && (
                  <p>
                    <span className="text-4xl font-bold">$0</span>
                    <span className="text-muted-foreground"> forever</span>
                  </p>
                )}
                {isPro && selected && (
                  <>
                    <p>
                      <span className="text-4xl font-bold">
                        {formatPrice(Math.round(monthlyEquivalent(selected)), selected.currency)}
                      </span>
                      <span className="text-muted-foreground"> / month</span>
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {selected.interval === 'year'
                        ? `${formatPrice(selected.unit_amount, selected.currency)} billed annually`
                        : 'Billed monthly, cancel anytime'}
                    </p>
                  </>
                )}
                {isPro && !selected && <p className="text-2xl font-bold">Coming soon</p>}
                {plan.id === 'enterprise' && <p className="text-4xl font-bold">Custom</p>}
              </div>

              <div className="mt-2">
                <PlanAction
                  plan={plan}
                  isCurrent={isCurrent}
                  currentTier={currentTier}
                  canBuy={!!selected && data.billing_enabled}
                  trialDays={data.trial_days}
                  busy={busy}
                  onUpgrade={onUpgrade ? () => onUpgrade(selected?.interval ?? billingInterval) : undefined}
                  onManage={onManage}
                />
              </div>

              <ul className="mt-6 space-y-3 border-t pt-6">
                {plan.highlights.map((line) => (
                  <li key={line} className="flex items-start gap-2 text-sm">
                    <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-600" />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface PlanActionProps {
  plan: Plan
  isCurrent: boolean
  currentTier?: Plan['id']
  canBuy: boolean
  trialDays: number
  busy?: boolean
  onUpgrade?: () => void
  onManage?: () => void
}

function PlanAction({ plan, isCurrent, currentTier, canBuy, trialDays, busy, onUpgrade, onManage }: PlanActionProps) {
  const signedIn = currentTier !== undefined

  if (plan.id === 'enterprise') {
    return (
      <Button asChild variant="outline" className="w-full">
        <Link to="/contact">Talk to us</Link>
      </Button>
    )
  }

  if (!signedIn) {
    return (
      <Button asChild className={cn('w-full', plan.id === 'pro' && 'bg-blue-600 hover:bg-blue-700')} variant={plan.id === 'pro' ? 'default' : 'outline'}>
        <Link to={plan.id === 'pro' ? '/register?plan=pro' : '/register'}>
          {plan.id === 'pro' ? 'Get started' : 'Start free'}
        </Link>
      </Button>
    )
  }

  if (plan.id === 'pro') {
    if (isCurrent || currentTier === 'enterprise') {
      return onManage && isCurrent ? (
        <Button variant="outline" className="w-full" onClick={onManage} disabled={busy}>
          {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Manage subscription
        </Button>
      ) : (
        <Button variant="outline" className="w-full" disabled>
          {isCurrent ? 'Current plan' : 'Included in your plan'}
        </Button>
      )
    }
    return (
      <Button className="w-full bg-blue-600 hover:bg-blue-700" onClick={onUpgrade} disabled={!canBuy || busy}>
        {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {!canBuy ? 'Unavailable right now' : trialDays > 0 ? `Start ${trialDays}-day free trial` : 'Upgrade to Pro'}
      </Button>
    )
  }

  // Free card for a signed-in user.
  return (
    <Button variant="outline" className="w-full" disabled>
      {isCurrent ? 'Current plan' : 'Included'}
    </Button>
  )
}
