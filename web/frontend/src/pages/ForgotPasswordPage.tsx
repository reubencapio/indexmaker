import { useState } from 'react'
import { Link } from 'react-router-dom'
import { LineChart, ArrowLeft, Mail, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'

export function ForgotPasswordPage() {
    const [email, setEmail] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isSubmitted, setIsSubmitted] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setIsLoading(true)

        try {
            await api.post('/auth/forgot-password', { email })
            setIsSubmitted(true)
        } catch (err: any) {
            // Always show success to prevent email enumeration
            setIsSubmitted(true)
        } finally {
            setIsLoading(false)
        }
    }

    if (isSubmitted) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-4">
                <div className="w-full max-w-md">
                    <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
                        <div className="text-center mb-6">
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
                                <CheckCircle className="h-8 w-8 text-green-600" />
                            </div>
                            <h1 className="text-2xl font-bold text-gray-900">Check your email</h1>
                            <p className="text-gray-600 mt-2">
                                If an account exists for <strong>{email}</strong>, we've sent a password reset link.
                            </p>
                        </div>

                        <div className="bg-blue-50 rounded-lg p-4 mb-6">
                            <p className="text-sm text-blue-800">
                                <strong>Didn't receive the email?</strong> Check your spam folder, or make sure you entered the correct email address.
                            </p>
                        </div>

                        <div className="space-y-3">
                            <Button
                                variant="outline"
                                className="w-full"
                                onClick={() => {
                                    setIsSubmitted(false)
                                    setEmail('')
                                }}
                            >
                                Try a different email
                            </Button>
                            <Link to="/login" className="block">
                                <Button variant="ghost" className="w-full">
                                    <ArrowLeft className="h-4 w-4 mr-2" />
                                    Back to login
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-4">
            <div className="w-full max-w-md">
                <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <Link to="/" className="inline-flex items-center gap-2 mb-6">
                            <div className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center">
                                <LineChart className="h-6 w-6 text-primary-foreground" />
                            </div>
                            <span className="font-bold text-xl">IndexMaker</span>
                        </Link>
                        <h1 className="text-2xl font-bold text-gray-900">Forgot password?</h1>
                        <p className="text-gray-600 mt-2">
                            No worries, we'll send you reset instructions.
                        </p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {error && (
                            <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-lg">
                                {error}
                            </div>
                        )}

                        <div className="space-y-2">
                            <Label htmlFor="email">Email address</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="you@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="pl-10"
                                    required
                                    autoFocus
                                />
                            </div>
                        </div>

                        <Button type="submit" className="w-full" disabled={isLoading}>
                            {isLoading ? 'Sending...' : 'Send reset link'}
                        </Button>
                    </form>

                    {/* Back to login */}
                    <div className="mt-6 text-center">
                        <Link
                            to="/login"
                            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
                        >
                            <ArrowLeft className="h-4 w-4 mr-1" />
                            Back to login
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}
