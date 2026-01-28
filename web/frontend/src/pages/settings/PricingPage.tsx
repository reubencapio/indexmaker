import { Link } from 'react-router-dom'
import { CheckCircle, Crown, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'

const tiers = [
    {
        id: 'free',
        name: 'Free',
        price: '$0',
        period: '/month',
        description: 'Perfect for getting started',
        features: ['3 custom indices', 'Basic backtesting', 'Daily updates', 'Email support'],
    },
    {
        id: 'pro',
        name: 'Pro',
        price: '$19.99',
        period: '/year',
        description: 'For serious investors',
        features: ['25 custom indices', 'Advanced backtesting', 'Real-time updates', 'API access', 'Priority support'],
        popular: true,
    },
    {
        id: 'enterprise',
        name: 'Enterprise',
        price: 'Custom',
        description: 'For institutions',
        features: ['Unlimited indices', 'White-label options', 'Dedicated support', 'Custom integrations', 'SLA guarantee'],
        contactOnly: true,
    },
]

export function PricingPage() {
    const { user } = useAuth()
    const currentTier = user?.tier || 'free'

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <div className="text-center">
                <h1 className="text-3xl font-bold">Upgrade Your Plan</h1>
                <p className="text-muted-foreground mt-2">
                    Choose the plan that best fits your needs
                </p>
            </div>

            {/* Current Plan Banner */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                        <Crown className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                        <p className="font-medium capitalize">Current Plan: {currentTier}</p>
                        <p className="text-sm text-muted-foreground">
                            {currentTier === 'free' ? 'Upgrade to unlock more features' : 'Thank you for being a Pro member!'}
                        </p>
                    </div>
                </div>
            </div>

            {/* Pricing Cards */}
            <div className="grid md:grid-cols-3 gap-6">
                {tiers.map((tier) => {
                    const isCurrent = tier.id === currentTier
                    const isUpgrade = tier.id === 'pro' && currentTier === 'free'

                    return (
                        <div
                            key={tier.id}
                            className={`bg-card rounded-xl p-6 border-2 transition-all ${isCurrent
                                ? 'border-primary ring-2 ring-primary/20'
                                : tier.popular
                                    ? 'border-primary/50'
                                    : 'border-border hover:border-primary/30'
                                }`}
                        >
                            {isCurrent && (
                                <span className="inline-flex items-center gap-1 bg-primary text-primary-foreground text-xs font-semibold px-3 py-1 rounded-full mb-4">
                                    <CheckCircle className="h-3 w-3" />
                                    Current Plan
                                </span>
                            )}
                            {tier.popular && !isCurrent && (
                                <span className="inline-flex items-center gap-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-semibold px-3 py-1 rounded-full mb-4">
                                    <Sparkles className="h-3 w-3" />
                                    Most Popular
                                </span>
                            )}

                            <h3 className="text-xl font-bold">{tier.name}</h3>
                            <p className="text-sm text-muted-foreground mt-1">{tier.description}</p>

                            <div className="mt-4 mb-6">
                                <span className="text-3xl font-bold">{tier.price}</span>
                                {tier.period && <span className="text-muted-foreground">{tier.period}</span>}
                            </div>

                            <ul className="space-y-2 mb-6">
                                {tier.features.map((feature) => (
                                    <li key={feature} className="flex items-center gap-2 text-sm">
                                        <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                                        <span>{feature}</span>
                                    </li>
                                ))}
                            </ul>

                            {isCurrent ? (
                                <Button className="w-full" variant="outline" disabled>
                                    Current Plan
                                </Button>
                            ) : tier.contactOnly ? (
                                <Link to="/contact">
                                    <Button className="w-full" variant="outline">
                                        Contact Sales
                                    </Button>
                                </Link>
                            ) : isUpgrade ? (
                                <Button className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700">
                                    Upgrade to Pro
                                </Button>
                            ) : (
                                <Button className="w-full" variant="outline">
                                    Select Plan
                                </Button>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* FAQ / Help */}
            <div className="text-center text-sm text-muted-foreground">
                <p>
                    Have questions?{' '}
                    <Link to="/contact" className="text-primary hover:underline">
                        Contact our support team
                    </Link>
                </p>
            </div>
        </div>
    )
}
