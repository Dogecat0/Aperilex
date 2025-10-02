import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { GlobalNav } from './GlobalNav'
import { GuidanceSidebar } from './GuidanceSidebar'
import { SearchBar } from './SearchBar'

export function AppShell() {
  const [isGuidanceVisible, setIsGuidanceVisible] = useState(false)

  return (
    <div
      className="relative min-h-screen"
      style={{ background: 'var(--surfaces-base)', color: 'var(--text-primary)' }}
    >
      <GlobalNav />

      <div className="relative mx-auto w-full max-w-7xl px-5 py-6">
        <div
          className={`flex flex-col gap-4 ${
            isGuidanceVisible ? 'lg:flex-row lg:items-start lg:gap-6' : ''
          }`}
        >
          <div className="flex w-full flex-col gap-4 lg:gap-5">
            <div className="flex flex-col gap-3">
              <SearchBar />
              {!isGuidanceVisible ? (
                <div className="hidden justify-end lg:flex">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => setIsGuidanceVisible(true)}
                  >
                    Show guidance
                  </Button>
                </div>
              ) : null}
            </div>
            <main className="flex-1">
              <Outlet />
            </main>
          </div>

          {isGuidanceVisible ? (
            <GuidanceSidebar onRequestClose={() => setIsGuidanceVisible(false)} />
          ) : null}
        </div>
      </div>
    </div>
  )
}
