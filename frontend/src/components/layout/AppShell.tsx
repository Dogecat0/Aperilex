import { Outlet } from 'react-router-dom'
import { GlobalNav } from './GlobalNav'
import { GuidanceSidebar } from './GuidanceSidebar'
import { SearchBar } from './SearchBar'

export function AppShell() {
  return (
    <div className="min-h-screen" style={{ background: 'var(--colors-background)' }}>
      <GlobalNav />

      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 lg:flex-row">
        <div className="flex w-full flex-1 flex-col gap-6">
          <SearchBar />
          <main
            className="flex-1 rounded-3xl border px-6 py-6"
            style={{
              background: 'var(--colors-surface)',
              borderColor: 'var(--colors-border)',
              color: 'var(--colors-foreground)',
              boxShadow: 'var(--shadows-soft)',
            }}
          >
            <Outlet />
          </main>
        </div>

        <GuidanceSidebar />
      </div>
    </div>
  )
}
