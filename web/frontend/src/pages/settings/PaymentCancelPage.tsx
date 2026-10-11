import { Link } from 'react-router-dom'
import { XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function PaymentCancelPage() {
    return (
        <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
            <div className="h-20 w-20 bg-muted rounded-full flex items-center justify-center mb-6">
                <XCircle className="h-10 w-10 text-muted-foreground" />
            </div>

            <h1 className="text-3xl font-bold mb-2">Checkout cancelled</h1>
            <p className="text-muted-foreground mb-8 max-w-md">
                No payment was taken and your plan hasn't changed. You can upgrade whenever you're ready.
            </p>

            <div className="flex gap-4">
                <Link to="/pricing">
                    <Button size="lg">Back to plans</Button>
                </Link>
                <Link to="/dashboard">
                    <Button variant="outline" size="lg">Back to Dashboard</Button>
                </Link>
            </div>
        </div>
    )
}
