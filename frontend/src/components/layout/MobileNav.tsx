import { useLocation } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/Button'
import { NavMenu } from '@/components/navigation/NavMenu'

export function MobileNav() {
  const { toggleMobileNav } = useAppStore()
  const location = useLocation()

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
        onClick={toggleMobileNav}
      />

      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-background border-r lg:hidden">
        <div className="flex h-16 items-center justify-between px-4 border-b">
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">A</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-primary">Aperilex</h1>
            </div>
          </div>

          <Button variant="ghost" size="sm" onClick={toggleMobileNav}>
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </Button>
        </div>

        <div className="flex grow flex-col gap-y-5 overflow-y-auto px-6 py-4">
          <nav className="flex flex-1 flex-col">
            <ul role="list" className="flex flex-1 flex-col gap-y-7">
              <li>
                <NavMenu currentPath={location.pathname} onNavigate={toggleMobileNav} />
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </>
  )
}
