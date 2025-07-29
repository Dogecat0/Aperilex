import { useState, useEffect } from 'react'
import { useAppStore } from '@/lib/store'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

export function QuickSearch() {
  const { quickSearchOpen, toggleQuickSearch } = useAppStore()
  const [query, setQuery] = useState('')

  // Handle keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        toggleQuickSearch()
      }
      if (e.key === 'Escape' && quickSearchOpen) {
        toggleQuickSearch()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [quickSearchOpen, toggleQuickSearch])

  if (!quickSearchOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm"
        onClick={toggleQuickSearch}
      />

      {/* Modal */}
      <div className="fixed left-[50%] top-[50%] z-50 w-full max-w-lg translate-x-[-50%] translate-y-[-50%] border bg-background p-6 shadow-lg rounded-lg">
        <div className="space-y-4">
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Quick Search</h2>
            <p className="text-sm text-muted-foreground">
              Search for companies, filings, or analyses
            </p>
          </div>

          <div className="space-y-4">
            <Input
              placeholder="Search..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />

            {/* Search Results Placeholder */}
            <div className="space-y-2">
              {query ? (
                <div className="text-sm text-muted-foreground">
                  Search functionality will be implemented in future phases
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-muted-foreground">RECENT SEARCHES</div>
                  <div className="text-sm text-muted-foreground">No recent searches</div>
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={toggleQuickSearch}>
              Cancel
            </Button>
            <Button disabled={!query}>Search</Button>
          </div>
        </div>
      </div>
    </>
  )
}
