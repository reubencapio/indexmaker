import { Outlet, Link } from 'react-router-dom'
import { LineChart } from 'lucide-react'

export function AuthLayout() {
  return (
    <div className="min-h-screen flex">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary p-12 flex-col justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="h-10 w-10 rounded-lg bg-primary-foreground/20 flex items-center justify-center">
            <LineChart className="h-6 w-6 text-primary-foreground" />
          </div>
          <span className="font-bold text-2xl text-primary-foreground">IndexMaker</span>
        </Link>

        <div className="space-y-6">
          <h1 className="text-4xl font-bold text-primary-foreground">
            Build Custom Financial Indices
          </h1>
          <p className="text-lg text-primary-foreground/80">
            Turn an investment idea into a rules-based index, test it against
            history, and share the results.
          </p>
          <div className="grid grid-cols-2 gap-4 pt-6">
            <div className="bg-primary-foreground/10 rounded-lg p-4">
              <h3 className="font-semibold text-primary-foreground">Easy Index Builder</h3>
              <p className="text-sm text-primary-foreground/70">
                Intuitive wizard to create indices in minutes
              </p>
            </div>
            <div className="bg-primary-foreground/10 rounded-lg p-4">
              <h3 className="font-semibold text-primary-foreground">Historical Backtests</h3>
              <p className="text-sm text-primary-foreground/70">
                Test strategies against years of data
              </p>
            </div>
            <div className="bg-primary-foreground/10 rounded-lg p-4">
              <h3 className="font-semibold text-primary-foreground">Real Analytics</h3>
              <p className="text-sm text-primary-foreground/70">
                Risk and return computed from daily market prices
              </p>
            </div>
            <div className="bg-primary-foreground/10 rounded-lg p-4">
              <h3 className="font-semibold text-primary-foreground">Share and Embed</h3>
              <p className="text-sm text-primary-foreground/70">
                Publish a live page or embed a chart anywhere
              </p>
            </div>
          </div>
        </div>

        <p className="text-sm text-primary-foreground/60">
          © {new Date().getFullYear()} IndexMaker. For research only; not investment advice.
        </p>
      </div>

      {/* Right panel - auth form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
