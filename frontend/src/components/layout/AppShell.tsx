import { Outlet } from 'react-router-dom'
import { useThemeTokens } from '@/components/ThemeProvider'
import { GlobalNav } from './GlobalNav'
import { GuidanceSidebar } from './GuidanceSidebar'
import { SearchBar } from './SearchBar'

export function AppShell() {
  const tokens = useThemeTokens()

  const haloGradient =
    tokens.name === 'dark'
      ? [
          'radial-gradient(120% 140% at 82% -12%, var(--learning-halo) 0%, rgba(6, 17, 37, 0) 68%)',
          'radial-gradient(85% 130% at 12% 0%, rgba(170, 183, 221, 0.25) 0%, rgba(6, 17, 37, 0) 70%)',
        ].join(', ')
      : [
          'radial-gradient(120% 135% at 80% -10%, var(--learning-halo) 0%, rgba(245, 247, 255, 0) 65%)',
          'radial-gradient(90% 120% at 10% 5%, rgba(143, 134, 228, 0.18) 0%, rgba(245, 247, 255, 0) 70%)',
        ].join(', ')

  return (
    <div
      className="relative min-h-screen overflow-hidden"
      style={{ background: 'var(--brand-background)', color: 'var(--text-primary)' }}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{ backgroundImage: haloGradient, opacity: tokens.name === 'dark' ? 0.8 : 0.85 }}
      />
      <GlobalNav />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-4 px-5 py-6 lg:flex-row lg:gap-6">
        <div className="flex w-full flex-1 flex-col gap-4 lg:gap-5">
          <SearchBar />
          <main
            className="flex-1 rounded-2xl border"
            style={{
              background: 'var(--surfaces-raised)',
              borderColor: 'var(--lines-subtle)',
              color: 'var(--text-primary)',
              boxShadow: 'var(--shadows-medium)',
              padding: 'var(--spacing-xl)',
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
