import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { UPGRADE_EVENT, type UpgradeRequiredDetail } from '@/lib/api'

/**
 * Opens whenever any API call is refused for needing a higher plan. Mounted once
 * in the app shell, so every limit and paid feature gets the same prompt without
 * each page having to know which of its actions are gated.
 */
export function UpgradeDialog() {
  const [detail, setDetail] = useState<UpgradeRequiredDetail | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const onUpgradeRequired = (event: Event) => setDetail((event as CustomEvent<UpgradeRequiredDetail>).detail)
    window.addEventListener(UPGRADE_EVENT, onUpgradeRequired)
    return () => window.removeEventListener(UPGRADE_EVENT, onUpgradeRequired)
  }, [])

  useEffect(() => {
    if (!detail) return
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && setDetail(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [detail])

  if (!detail) return null

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
      onClick={() => setDetail(null)}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="upgrade-title"
        className="relative w-full max-w-md rounded-xl border bg-background p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          aria-label="Close"
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
          onClick={() => setDetail(null)}
        >
          <X className="h-5 w-5" />
        </button>
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
          <Sparkles className="h-6 w-6 text-blue-600" />
        </div>
        <h2 id="upgrade-title" className="text-xl font-semibold">
          {detail.limit ? "You've reached your plan limit" : 'This is a Pro feature'}
        </h2>
        <p className="mt-2 text-muted-foreground">{detail.message}</p>
        <div className="mt-6 flex gap-3">
          <Button variant="outline" className="flex-1" onClick={() => setDetail(null)}>
            Not now
          </Button>
          <Button
            className="flex-1 bg-blue-600 hover:bg-blue-700"
            onClick={() => {
              setDetail(null)
              navigate('/pricing')
            }}
          >
            See plans
          </Button>
        </div>
      </div>
    </div>
  )
}
