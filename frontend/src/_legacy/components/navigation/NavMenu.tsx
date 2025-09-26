import { Link } from 'react-router-dom'

interface NavMenuProps {
  currentPath: string
  onNavigate?: () => void
}

const navigationItems = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
        />
      </svg>
    ),
  },
  {
    id: 'companies',
    label: 'Companies',
    href: '/companies',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m2 0h3M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
        />
      </svg>
    ),
  },
  {
    id: 'analyses',
    label: 'Analyses',
    href: '/analyses',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
  },
  {
    id: 'filings',
    label: 'Filings',
    href: '/filings',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
  },
]

export function NavMenu({ currentPath, onNavigate }: NavMenuProps) {
  const isActive = (href: string) => {
    return href === '/' ? currentPath === href : currentPath.startsWith(href)
  }

  return (
    <ul role="list" className="-mx-2 space-y-1">
      {navigationItems.map((item) => {
        const active = isActive(item.href)

        return (
          <li key={item.id}>
            <Link
              to={item.href}
              onClick={onNavigate}
              className={`
                group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold transition-colors
                ${
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-foreground hover:text-primary hover:bg-accent'
                }
              `}
            >
              <span
                className={`
                ${active ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-primary'}
              `}
              >
                {item.icon}
              </span>
              {item.label}
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
