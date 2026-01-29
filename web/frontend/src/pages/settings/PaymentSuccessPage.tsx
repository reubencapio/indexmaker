import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'

export function PaymentSuccessPage() {
    const [searchParams] = useSearchParams()
    const sessionId = searchParams.get('session_id')
    const { refetchUser } = useAuth()

    useEffect(() => {
        // Refresh user data to get updated tier
        if (sessionId) {
            setTimeout(() => {
                refetchUser()
            }, 2000) // Small delay to allow webhook to process
        }
    }, [sessionId, refetchUser])

    return (
        <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
            <div className="h-20 w-20 bg-green-100 rounded-full flex items-center justify-center mb-6">
                <CheckCircle className="h-10 w-10 text-green-600" />
            </div>

            <h1 className="text-3xl font-bold mb-2">Payment Successful!</h1>
            <p className="text-muted-foreground mb-8 max-w-md">
                Thank you for upgrading to Pro. Your account has been updated with all the Pro features.
            </p>

            <div className="flex gap-4">
                <Link to="/dashboard">
                    <Button size="lg">Go to Dashboard</Button>
                </Link>
                <Link to="/indices/new">
                    <Button variant="outline" size="lg">Create New Index</Button>
                </Link>
            </div>
        </div>
    )
}
