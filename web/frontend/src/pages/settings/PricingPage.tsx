import { Link } from 'react-router-dom'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PlanCards } from '@/components/billing/PlanCards'
import { useAuth } from '@/hooks/useAuth'
import { useBillingActions, usePlans, useSubscription } from '@/hooks/useBilling'
import type { Plan } from '@/lib/api'

const faqs = [
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. Cancel from billing settings in two clicks. You keep Pro until the end of the period you have paid for, then move to the Free plan.',
  },
  {
    q: 'What happens to my indices if I downgrade?',
    a: 'Nothing is deleted. Every index, backtest and share link stays readable. You will not be able to create new ones beyond the Free limits until you are back under them or upgrade again.',
  },
  {
    q: 'Can I switch between monthly and annual?',
    a: 'Yes, from billing settings. Stripe prorates the change, so you only pay the difference.',
  },
  {
    q: 'Where does the market data come from?',
    a: 'Prices and fundamentals come from the data source selected in your settings (Yahoo Finance by default). You can also connect your own data. Figures are for research and are not investment advice.',
  },
  {
    q: 'Is my payment information safe?',
    a: 'Payments are handled entirely by Stripe. Card details never reach our servers.',
  },
]

export function PricingPage() {
  const { user } = useAuth()
  const plans = usePlans()
  const subscription = useSubscription()
  const { startCheckout, openPortal, pending } = useBillingActions()
  const currentTier = (subscription.data?.tier ?? user?.tier ?? 'free') as Plan['id']

  return (
    <div className="mx-auto max-w-5xl space-y-12">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Plans and pricing</h1>
        <p className="mt-2 text-muted-foreground">
          Start free. Upgrade when you need deeper history, exports and webhooks.
        </p>
      </div>

      {plans.isLoading && (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {plans.isError && (
        <div className="flex flex-col items-center gap-4 rounded-xl border p-8 text-center">
          <AlertTriangle className="h-8 w-8 text-amber-500" />
          <p>We couldn't load plans just now.</p>
          <Button variant="outline" onClick={() => plans.refetch()}>
            Try again
          </Button>
        </div>
      )}

      {plans.data && (
        <>
          {!plans.data.billing_enabled && currentTier === 'free' && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              Online checkout isn't available at the moment.{' '}
              <Link to="/contact" className="font-medium underline">
                Contact us
              </Link>{' '}
              and we'll set up your upgrade.
            </div>
          )}
          <PlanCards
            data={plans.data}
            currentTier={currentTier}
            onUpgrade={startCheckout}
            onManage={subscription.data?.has_billing_account ? openPortal : undefined}
            busy={pending !== null}
          />
        </>
      )}

      <div className="mx-auto max-w-3xl">
        <h2 className="mb-6 text-center text-2xl font-bold">Questions</h2>
        <div className="divide-y rounded-xl border bg-card">
          {faqs.map((faq) => (
            <details key={faq.q} className="group p-5">
              <summary className="flex cursor-pointer list-none items-center justify-between font-medium">
                {faq.q}
                <span className="ml-4 text-muted-foreground transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-sm text-muted-foreground">{faq.a}</p>
            </details>
          ))}
        </div>
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Something else?{' '}
          <Link to="/contact" className="text-primary underline-offset-4 hover:underline">
            Ask us
          </Link>
        </p>
      </div>
    </div>
  )
}
