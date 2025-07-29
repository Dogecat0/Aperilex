import { useLocation } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { NavMenu } from '@/components/navigation/NavMenu'

export function Sidebar() {
  const { sidebarOpen } = useAppStore()
  const location = useLocation()

  if (!sidebarOpen) return null

  return (
    <aside className="hidden lg:fixed lg:inset-y-0 lg:z-40 lg:flex lg:w-64 lg:flex-col lg:pt-16">
      <div className="flex grow flex-col gap-y-5 overflow-y-auto border-r bg-background px-6 pb-4">
        <nav className="flex flex-1 flex-col">
          <ul role="list" className="flex flex-1 flex-col gap-y-7">
            <li>
              <NavMenu currentPath={location.pathname} />
            </li>

            {/* Recent Activity Section */}
            <li>
              <div className="text-xs font-semibold leading-6 text-muted-foreground">
                Recent Activity
              </div>
              <ul role="list" className="-mx-2 mt-2 space-y-1">
                <li>
                  <div className="text-sm text-muted-foreground px-2 py-1">No recent activity</div>
                </li>
              </ul>
            </li>

            {/* Quick Actions */}
            <li className="mt-auto">
              <div className="space-y-2">
                <button className="w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
                  New Analysis
                </button>
                <button className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground">
                  Import Filing
                </button>
              </div>
            </li>
          </ul>
        </nav>
      </div>
    </aside>
  )
}
