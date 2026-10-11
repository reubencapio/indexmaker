import { Link } from 'react-router-dom'
import {
  LineChart,
  Sparkles,
  History,
  BarChart3,
  Scale,
  Share2,
  Database,
  ArrowRight,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PlanCards } from '@/components/billing/PlanCards'
import { usePlans } from '@/hooks/useBilling'
import { useAuthStore } from '@/store/authStore'

const features = [
  {
    icon: Sparkles,
    title: 'Describe it, and it is built',
    description:
      'Type "top 30 US dividend payers, capped at 5% each" and get a working index with real constituents, ready to refine.',
  },
  {
    icon: Scale,
    title: 'Proper index maths',
    description:
      'Levels are divisor-based, like the indices you benchmark against. Rebalances and corporate actions never cause a jump in the level.',
  },
  {
    icon: History,
    title: 'Backtests you can trust',
    description:
      'Point-in-time simulation on your rebalancing schedule, with transaction costs charged on turnover, so results are not flattered.',
  },
  {
    icon: BarChart3,
    title: 'Performance and risk analytics',
    description:
      'Return, volatility, drawdown, Sharpe, beta and tracking error against the benchmark you choose, computed from daily prices.',
  },
  {
    icon: Share2,
    title: 'Share and embed',
    description:
      'Publish a live page for any index, or drop a chart into your own site or client report with one line of HTML.',
  },
  {
    icon: Database,
    title: 'Bring your own data',
    description:
      'Start with built-in market data, or connect a CSV, API or database to define your own universe.',
  },
]

const steps = [
  {
    title: 'Define the rules',
    description: 'Pick a universe, selection criteria, weighting and caps, or let the AI builder draft them from a sentence.',
  },
  {
    title: 'Test it against history',
    description: 'Backtest against a benchmark and check the analytics before you rely on it.',
  },
  {
    title: 'Run it',
    description: 'Track drift, rebalance on schedule, and share or deliver the results wherever they are needed.',
  },
]

export function LandingPage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const plans = usePlans()

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur">
        <div className="container mx-auto flex items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <LineChart className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">IndexMaker</span>
          </Link>
          <div className="flex items-center gap-2 sm:gap-4">
            <a href="#features" className="hidden text-sm text-muted-foreground hover:text-foreground sm:block">
              Features
            </a>
            <a href="#pricing" className="hidden text-sm text-muted-foreground hover:text-foreground sm:block">
              Pricing
            </a>
            {isAuthenticated ? (
              <Button asChild>
                <Link to="/dashboard">Open dashboard</Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost">
                  <Link to="/login">Sign in</Link>
                </Button>
                <Button asChild>
                  <Link to="/register">Get started</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-4 py-20 sm:px-6 sm:py-28">
        <div className="container mx-auto max-w-4xl text-center">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" />
            Free to start. No card required.
          </p>
          <h1 className="mb-6 text-4xl font-bold tracking-tight sm:text-6xl">
            Build, backtest and run your own stock index
          </h1>
          <p className="mx-auto mb-8 max-w-2xl text-lg text-muted-foreground sm:text-xl">
            Turn an investment idea into a rules-based index in minutes. Test it against history, see how
            it really behaves, and share it with clients or your audience.
          </p>
          <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg" className="gap-2">
              <Link to={isAuthenticated ? '/indices/new' : '/register'}>
                {isAuthenticated ? 'Create an index' : 'Start building free'} <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <a href="#pricing">See pricing</a>
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="scroll-mt-20 bg-muted/50 px-4 py-20 sm:px-6">
        <div className="container mx-auto">
          <h2 className="mb-3 text-center text-3xl font-bold">Everything from idea to live index</h2>
          <p className="mx-auto mb-12 max-w-2xl text-center text-muted-foreground">
            The tools index providers use, without the six-figure licence.
          </p>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.title} className="rounded-xl border bg-card p-6">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <feature.icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="mb-2 text-lg font-semibold">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="px-4 py-20 sm:px-6">
        <div className="container mx-auto max-w-5xl">
          <h2 className="mb-12 text-center text-3xl font-bold">How it works</h2>
          <ol className="grid gap-8 md:grid-cols-3">
            {steps.map((step, i) => (
              <li key={step.title}>
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground">
                  {i + 1}
                </div>
                <h3 className="mb-2 text-lg font-semibold">{step.title}</h3>
                <p className="text-muted-foreground">{step.description}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="scroll-mt-20 bg-muted/50 px-4 py-20 sm:px-6">
        <div className="container mx-auto max-w-5xl">
          <h2 className="mb-3 text-center text-3xl font-bold">Simple pricing</h2>
          <p className="mx-auto mb-12 max-w-2xl text-center text-muted-foreground">
            Build and backtest for free. Upgrade when you need deeper history, exports and webhooks.
          </p>
          {plans.data ? (
            <PlanCards data={plans.data} />
          ) : plans.isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="text-center">
              <Button asChild size="lg">
                <Link to="/register">Start free</Link>
              </Button>
            </div>
          )}
        </div>
      </section>

      {/* Closing call to action */}
      <section className="px-4 py-20 sm:px-6">
        <div className="container mx-auto max-w-3xl text-center">
          <h2 className="mb-4 text-3xl font-bold">Your first index takes about two minutes</h2>
          <p className="mb-8 text-muted-foreground">Three indices are free, for as long as you like.</p>
          <Button asChild size="lg" className="gap-2">
            <Link to={isAuthenticated ? '/indices/new' : '/register'}>
              Create an index <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t px-4 py-10 sm:px-6">
        <div className="container mx-auto flex flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-primary">
              <LineChart className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-semibold">IndexMaker</span>
          </div>
          <div className="flex gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#pricing" className="hover:text-foreground">Pricing</a>
            <Link to="/contact" className="hover:text-foreground">Contact</Link>
          </div>
          <p className="text-center text-sm text-muted-foreground">
            © {new Date().getFullYear()} IndexMaker. For research and information only; not investment advice.
          </p>
        </div>
      </footer>
    </div>
  )
}
