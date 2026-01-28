import { Link } from 'react-router-dom'
import { LineChart, Zap, Shield, BarChart3, ArrowRight, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

const features = [
  {
    icon: LineChart,
    title: 'Custom Index Builder',
    description: 'Create indices with any weighting scheme: equal, market cap, or custom factor-based.',
  },
  {
    icon: BarChart3,
    title: 'Historical Backtesting',
    description: 'Test your strategies against years of historical data with detailed analytics.',
  },
  {
    icon: Zap,
    title: 'Real-Time Updates',
    description: 'Get live market data and automatic index calculations throughout the day.',
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description: 'Bank-grade encryption and security for your index configurations.',
  },
]

const tiers = [
  {
    name: 'Free',
    price: '$0',
    period: '/month',
    description: 'Perfect for getting started',
    features: ['3 custom indices', 'Basic backtesting', 'Daily updates', 'Email support'],
  },
  {
    name: 'Pro',
    price: '$19.99',
    period: '/year',
    description: 'For serious investors',
    features: ['25 custom indices', 'Advanced backtesting', 'Real-time updates', 'API access', 'Priority support'],
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    description: 'For institutions',
    features: ['Unlimited indices', 'White-label options', 'Dedicated support', 'Custom integrations', 'SLA guarantee'],
    contactOnly: true,
  },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="border-b">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <LineChart className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-xl">IndexMaker</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link to="/register">
              <Button>Get Started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-20 px-6">
        <div className="container mx-auto text-center max-w-4xl">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
            Build Custom Financial Indices in Minutes
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Create, backtest, and manage your own indices with powerful tools,
            real-time market data, and institutional-grade methodology.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link to="/register">
              <Button size="lg" className="gap-2">
                Start Building Free <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline">
                View Demo
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-muted/50">
        <div className="container mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            Everything You Need to Build Indices
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature) => (
              <div key={feature.title} className="bg-card rounded-xl p-6 border">
                <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                  <feature.icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6">
        <div className="container mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">Simple, Transparent Pricing</h2>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
            Choose the plan that fits your needs. All plans include our core features.
          </p>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={`bg-card rounded-xl p-8 border ${tier.popular ? 'border-primary ring-2 ring-primary' : ''
                  }`}
              >
                {tier.popular && (
                  <span className="inline-block bg-primary text-primary-foreground text-xs font-semibold px-3 py-1 rounded-full mb-4">
                    Most Popular
                  </span>
                )}
                <h3 className="text-2xl font-bold">{tier.name}</h3>
                <p className="text-muted-foreground mt-2">{tier.description}</p>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-bold">{tier.price}</span>
                  {tier.period && <span className="text-muted-foreground">{tier.period}</span>}
                </div>
                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-primary" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link to={tier.contactOnly ? '/contact' : '/register'}>
                  <Button className="w-full" variant={tier.popular ? 'default' : 'outline'}>
                    {tier.contactOnly ? 'Contact Us' : 'Get Started'}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12 px-6">
        <div className="container mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded bg-primary flex items-center justify-center">
              <LineChart className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-semibold">IndexMaker</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © 2024 IndexMaker. All rights reserved. Not financial advice.
          </p>
        </div>
      </footer>
    </div>
  )
}
