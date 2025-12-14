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
            Create, backtest, and manage your own indices with powerful tools
            and real-time market data.
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
              <h3 className="font-semibold text-primary-foreground">Live Market Data</h3>
              <p className="text-sm text-primary-foreground/70">
                Real-time prices from major exchanges
              </p>
            </div>
            <div className="bg-primary-foreground/10 rounded-lg p-4">
              <h3 className="font-semibold text-primary-foreground">API Access</h3>
              <p className="text-sm text-primary-foreground/70">
                Full programmatic control via REST API
              </p>
            </div>
          </div>
        </div>

        <p className="text-sm text-primary-foreground/60">
          © 2024 IndexMaker. All rights reserved.
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

