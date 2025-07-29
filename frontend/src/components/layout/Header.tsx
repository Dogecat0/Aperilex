import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/Button'
import { QuickSearch } from '@/components/navigation/QuickSearch'
import { UserPreferences } from '@/components/navigation/UserPreferences'

export function Header() {
  const { toggleSidebar, toggleMobileNav, toggleQuickSearch } = useAppStore()

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* Left Section: Menu Toggle + Logo */}
        <div className="flex items-center space-x-4">
          {/* Mobile Menu Toggle */}
          <Button variant="ghost" size="sm" className="lg:hidden" onClick={toggleMobileNav}>
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </Button>

          {/* Desktop Sidebar Toggle */}
          <Button
            variant="ghost"
            size="sm"
            className="hidden lg:inline-flex"
            onClick={toggleSidebar}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </Button>

          {/* Logo */}
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">A</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-primary">Aperilex</h1>
              <p className="text-xs text-muted-foreground hidden sm:block">
                Financial Analysis Made Simple
              </p>
            </div>
          </div>
        </div>

        {/* Center Section: Quick Search */}
        <div className="hidden md:flex flex-1 max-w-md mx-8">
          <Button
            variant="outline"
            className="w-full justify-start text-muted-foreground"
            onClick={toggleQuickSearch}
          >
            <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            Search companies, filings...
            <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>
        </div>

        {/* Right Section: Actions */}
        <div className="flex items-center space-x-2">
          {/* Mobile Search */}
          <Button variant="ghost" size="sm" className="md:hidden" onClick={toggleQuickSearch}>
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </Button>

          {/* User Preferences */}
          <UserPreferences />
        </div>
      </div>

      {/* Quick Search Modal */}
      <QuickSearch />
    </header>
  )
}
