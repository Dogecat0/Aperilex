import { Outlet } from 'react-router-dom'
import { GlobalNav } from './GlobalNav'
import { SearchBar } from './SearchBar'

export function AppShell() {
  return (
    <div
      className="relative min-h-screen"
      style={{ background: 'var(--surfaces-base)', color: 'var(--text-primary)' }}
    >
      <GlobalNav />

      <div className="relative mx-auto w-full max-w-7xl px-5 py-6">
        <div className="flex flex-col gap-4 lg:gap-5">
          <div className="flex flex-col gap-3">
            <SearchBar />
          </div>
          <main className="flex-1">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
