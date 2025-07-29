import { Outlet } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { MobileNav } from './MobileNav'
import { Footer } from './Footer'
import { Breadcrumb } from '@/components/navigation/Breadcrumb'

export function AppShell() {
  const { sidebarOpen, mobileNavOpen } = useAppStore()

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="flex">
        {/* Desktop Sidebar */}
        <Sidebar />

        {/* Mobile Navigation Overlay */}
        {mobileNavOpen && <MobileNav />}

        {/* Main Content */}
        <main
          className={`
          flex-1 transition-all duration-200 ease-in-out
          ${sidebarOpen ? 'lg:ml-64' : 'lg:ml-0'}
          min-h-[calc(100vh-4rem)]
        `}
        >
          <div className="container mx-auto px-4 py-6">
            <Breadcrumb />
            <Outlet />
          </div>
        </main>
      </div>

      <Footer />
    </div>
  )
}
