import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { LineChart as LineChartIcon, Loader2, Lock } from 'lucide-react'
import type { AxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { publicApi, type PublicIndexView } from '@/lib/api'
import { cn, formatDate, formatPercent } from '@/lib/utils'

const GRID_LIGHT = '#e1e0d9'
const GRID_DARK = '#2c2c2a'
const AXIS = '#898781'

const pct = (value: number | null, signed = false) =>
  value === null ? '–' : `${signed && value > 0 ? '+' : ''}${formatPercent(value)}`

const shortDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })

function useDark(theme: PublicIndexView['theme'] | undefined): boolean {
  if (theme === 'dark') return true
  if (theme === 'auto') return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  return false
}

function errorCode(error: unknown): string | undefined {
  const detail = (error as AxiosError<{ detail?: { code?: string } | string }>)?.response?.data?.detail
  return typeof detail === 'object' ? detail?.code : undefined
}

/**
 * The page behind a public share link (/public/:slug) and an embed iframe
 * (/embed/:token). Read-only and unauthenticated; `embed` drops the page chrome.
 */
export function PublicIndexPage({ embed = false }: { embed?: boolean }) {
  const { slug, token } = useParams<{ slug?: string; token?: string }>()
  const [password, setPassword] = useState<string>()
  const [passwordInput, setPasswordInput] = useState('')

  const query = useQuery({
    queryKey: ['public-index', embed ? token : slug, password],
    queryFn: () => (embed ? publicApi.widget(token!) : publicApi.share(slug!, password)),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const dark = useDark(query.data?.theme)
  const code = errorCode(query.error)

  if (query.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (code === 'password_required' || code === 'password_invalid') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
        <form
          className="w-full max-w-sm rounded-xl border bg-background p-6 shadow-sm"
          onSubmit={(e) => {
            e.preventDefault()
            setPassword(passwordInput)
          }}
        >
          <Lock className="mb-3 h-6 w-6 text-muted-foreground" />
          <h1 className="text-lg font-semibold">This index is password protected</h1>
          <p className="mt-1 text-sm text-muted-foreground">Enter the password you were given to view it.</p>
          <input
            type="password"
            autoFocus
            aria-label="Password"
            value={passwordInput}
            onChange={(e) => setPasswordInput(e.target.value)}
            className="mt-4 w-full rounded-lg border bg-background px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
          />
          {code === 'password_invalid' && <p className="mt-2 text-sm text-destructive">That password isn't right.</p>}
          <Button type="submit" className="mt-4 w-full" disabled={!passwordInput}>
            View index
          </Button>
        </form>
      </div>
    )
  }

  if (query.isError || !query.data) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-xl font-semibold">This link isn't available</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          It may have been switched off or expired. Ask whoever shared it for a new link.
        </p>
        {!embed && (
          <Button asChild variant="outline" className="mt-2">
            <Link to="/">Go to IndexMaker</Link>
          </Button>
        )}
      </div>
    )
  }

  const data = query.data
  const accent = data.primary_color || '#2a78d6'
  const grid = dark ? GRID_DARK : GRID_LIGHT
  const components = data.components ? [...data.components].sort((a, b) => b.weight - a.weight) : null

  return (
    <div
      className={cn('min-h-screen bg-background text-foreground', dark && 'dark')}
      style={data.background_color ? { backgroundColor: data.background_color } : undefined}
    >
      <div className={cn('mx-auto', embed ? 'p-4' : 'max-w-4xl px-4 py-10 sm:px-6')}>
        <header className="mb-6">
          <p className="font-mono text-sm text-muted-foreground">{data.identifier}</p>
          <h1 className={cn('font-bold', embed ? 'text-xl' : 'text-3xl')}>{data.title}</h1>
          {!embed && data.description && <p className="mt-2 max-w-2xl text-muted-foreground">{data.description}</p>}
          <div className="mt-4 flex flex-wrap items-baseline gap-x-6 gap-y-1">
            {data.current_value !== null && (
              <p className={cn('font-semibold tabular-nums', embed ? 'text-2xl' : 'text-4xl')}>
                {data.current_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            )}
            {data.stats?.total_return != null && (
              <p className="text-sm text-muted-foreground">
                <span className={cn('font-medium', data.stats.total_return >= 0 ? 'text-emerald-600' : 'text-red-600')}>
                  {pct(data.stats.total_return, true)}
                </span>{' '}
                over the period shown
              </p>
            )}
          </div>
        </header>

        {data.series && data.series.length > 1 && (
          <div className={cn('rounded-xl border bg-card p-4', embed ? 'h-56' : 'h-80')}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.series} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={grid} vertical={false} />
                <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={48} tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={{ stroke: grid }} />
                <YAxis domain={['auto', 'auto']} width={52} tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => v.toLocaleString('en-US', { maximumFractionDigits: 0 })} />
                <Tooltip
                  labelFormatter={(label: string) => formatDate(`${label}T00:00:00`)}
                  formatter={(value: number) => [value.toLocaleString('en-US', { maximumFractionDigits: 2 }), data.identifier]}
                  contentStyle={{ borderRadius: 8, borderColor: grid, fontSize: 13, color: '#0b0b0b' }}
                />
                <Area type="monotone" dataKey="value" stroke={accent} strokeWidth={2} fill={accent} fillOpacity={0.12} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {data.stats && (
          <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              ['Return', pct(data.stats.total_return, true)],
              ['Annualised', pct(data.stats.annualized_return, true)],
              ['Volatility', pct(data.stats.volatility)],
              ['Max drawdown', pct(data.stats.max_drawdown)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border bg-card p-4">
                <dt className="text-xs text-muted-foreground">{label}</dt>
                <dd className="mt-1 text-lg font-semibold tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
        )}

        {components && components.length > 0 && (
          <div className="mt-6 overflow-hidden rounded-xl border bg-card">
            <div className="border-b px-4 py-3">
              <h2 className="font-semibold">Constituents ({components.length})</h2>
            </div>
            <div className={cn('overflow-auto', embed && 'max-h-72')}>
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-left text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 font-medium">Ticker</th>
                    <th className="px-4 py-2 font-medium">Name</th>
                    <th className="hidden px-4 py-2 font-medium sm:table-cell">Sector</th>
                    <th className="px-4 py-2 text-right font-medium">Weight</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {components.map((c) => (
                    <tr key={c.ticker}>
                      <td className="px-4 py-2 font-mono font-medium">{c.ticker}</td>
                      <td className="px-4 py-2">{c.name || '–'}</td>
                      <td className="hidden px-4 py-2 text-muted-foreground sm:table-cell">{c.sector || '–'}</td>
                      <td className="px-4 py-2 text-right tabular-nums">{formatPercent(c.weight)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <footer className="mt-6 space-y-3 text-xs text-muted-foreground">
          <p>
            {data.as_of ? `Prices as of ${formatDate(`${data.as_of}T00:00:00`)}. ` : ''}
            Performance shows the current constituents over the period and is hypothetical. For information only; not investment advice.
          </p>
          {data.show_branding && (
            <a
              href={`${window.location.origin}/?ref=${embed ? 'embed' : 'share'}`}
              target={embed ? '_blank' : undefined}
              rel="noopener"
              className="inline-flex items-center gap-2 font-medium text-foreground hover:underline"
            >
              <span className="flex h-5 w-5 items-center justify-center rounded bg-primary">
                <LineChartIcon className="h-3 w-3 text-primary-foreground" />
              </span>
              Built with IndexMaker. Create your own index free
            </a>
          )}
        </footer>
      </div>
    </div>
  )
}
