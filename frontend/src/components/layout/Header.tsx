import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/Button'
import { UserPreferences } from '@/components/navigation/UserPreferences'
import { useNavigate } from 'react-router-dom'

export function Header() {
  const { toggleMobileNav } = useAppStore()
  const navigate = useNavigate()

  const handleLogoClick = () => {
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-50 mb-6 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
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

          {/* Logo - Clickable Home Button */}
          <button
            onClick={handleLogoClick}
            className="flex items-center space-x-2 hover:opacity-80 transition-opacity"
          >
            <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">A</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-primary">perilex</h1>
            </div>
          </button>
        </div>

        {/* Right Section: Actions */}
        <div className="flex items-center space-x-2">
          {/* User Preferences */}
          <UserPreferences />
        </div>
      </div>
    </header>
  )
}
