import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, RefreshCw, Terminal } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { indicesApi, getErrorMessage } from '@/lib/api'

export interface BuildInfo {
  as_of?: string
  data_source?: string
  candidates?: number
  exclusions?: Record<string, string>
  unconverted?: Record<string, string>
  /** Countries in the rules that the data source has no exchange for. */
  unscreened?: string[]
}

interface ReproduceCardProps {
  indexId: string
  identifier: string
  buildInfo?: BuildInfo | null
  /** True when the rules found the companies; false when the spec lists them. */
  screened: boolean
}

/** Exclusion reasons with how many candidates each one removed, most common first. */
export function summariseExclusions(exclusions: Record<string, string> = {}) {
  const counts = new Map<string, number>()
  for (const reason of Object.values(exclusions)) {
    counts.set(reason, (counts.get(reason) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([reason, count]) => ({ reason, count }))
    .sort((a, b) => b.count - a.count || a.reason.localeCompare(b.reason))
}

const MAX_REASONS = 6

/**
 * How this index was built, and everything needed to build it again.
 *
 * The members are not a list anyone chose: they are what the spec's rules give
 * for the recorded market data. The two downloads let anyone check that.
 */
export function ReproduceCard({ indexId, identifier, buildInfo, screened }: ReproduceCardProps) {
  const queryClient = useQueryClient()
  const [downloading, setDownloading] = useState<'spec' | 'data' | null>(null)

  const rebuild = useMutation({
    mutationFn: () => indicesApi.rebuild(indexId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', indexId] })
      toast.success('Rebuilding with today’s market data')
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Could not start the rebuild')),
  })

  const download = async (kind: 'spec' | 'data') => {
    setDownloading(kind)
    try {
      if (kind === 'spec') await indicesApi.downloadSpec(indexId, identifier)
      else await indicesApi.downloadBuildData(indexId, identifier)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Download failed'))
    } finally {
      setDownloading(null)
    }
  }

  const file = identifier.toLowerCase()
  const reasons = summariseExclusions(buildInfo?.exclusions)
  const excluded = Object.keys(buildInfo?.exclusions ?? {}).length
  const unconverted = Object.keys(buildInfo?.unconverted ?? {})
  const unscreened = buildInfo?.unscreened ?? []

  return (
    <section className="bg-card rounded-xl border p-6" aria-labelledby="reproduce-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="reproduce-heading" className="text-lg font-semibold">
            How this index was built
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {screened
              ? 'The rules chose the members. No one picked the companies.'
              : 'The members come from the companies named in the rules.'}{' '}
            The same rules with the same market data always give this result.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => rebuild.mutate()}
          disabled={rebuild.isPending}
          title="Apply the same rules to today's market data. Members can change."
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${rebuild.isPending ? 'animate-spin' : ''}`} />
          Rebuild with today’s data
        </Button>
      </div>

      {buildInfo && (
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">Built as of</dt>
            <dd className="font-medium">{buildInfo.as_of ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Market data</dt>
            <dd className="font-medium">{buildInfo.data_source ?? '-'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Companies considered</dt>
            <dd className="font-medium">{buildInfo.candidates?.toLocaleString() ?? '-'}</dd>
          </div>
        </dl>
      )}

      {reasons.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">
            {excluded.toLocaleString()} left out, by reason
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            {reasons.slice(0, MAX_REASONS).map(({ reason, count }) => (
              <li key={reason} className="flex gap-3">
                <span className="w-12 shrink-0 text-right tabular-nums text-foreground">
                  {count.toLocaleString()}
                </span>
                <span>{reason}</span>
              </li>
            ))}
            {reasons.length > MAX_REASONS && (
              <li className="pl-[3.75rem]">
                and {reasons.length - MAX_REASONS} other reasons, listed in the data file
              </li>
            )}
          </ul>
        </div>
      )}

      {unscreened.length > 0 && (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          Not searched: {unscreened.join(', ')}. {buildInfo?.data_source ?? 'The data source'}{' '}
          covers no stock exchange there, so companies listed only in{' '}
          {unscreened.length === 1 ? 'that country' : 'those countries'} are missing.
        </p>
      )}

      {unconverted.length > 0 && (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          No exchange rate was available for {unconverted.join(', ')}, so their market caps are
          in their own currency and their ranking may be off.
        </p>
      )}

      <div className="mt-6 border-t pt-4">
        <h3 className="flex items-center gap-2 text-sm font-medium">
          <Terminal className="h-4 w-4" />
          Reproduce it yourself
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Download the rules and the market data, then run the open-source{' '}
          <a
            href="https://github.com/reubencapio/indexforge"
            target="_blank"
            rel="noreferrer"
            className="underline hover:text-foreground"
          >
            indexforge
          </a>{' '}
          tool. It gives these members and weights on any computer, on any day.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => download('spec')}
            disabled={downloading !== null}
          >
            <Download className="mr-2 h-4 w-4" />
            Rules ({file}.yaml)
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => download('data')}
            disabled={downloading !== null}
          >
            <Download className="mr-2 h-4 w-4" />
            Market data ({file}.data.json)
          </Button>
        </div>
        <pre className="mt-3 overflow-x-auto rounded-lg bg-muted p-3 text-xs">
          <code>{`pip install indexforge
indexforge build ${file}.yaml --data ${file}.data.json`}</code>
        </pre>
      </div>
    </section>
  )
}
