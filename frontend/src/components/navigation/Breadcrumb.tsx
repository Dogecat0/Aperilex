import { Link } from 'react-router-dom'
import { useAppStore } from '@/lib/store'

export function Breadcrumb() {
  const { breadcrumbs } = useAppStore()

  if (breadcrumbs.length === 0) return null

  return (
    <nav aria-label="Breadcrumb" className="mb-4">
      <ol className="flex items-center space-x-2 text-sm text-muted-foreground">
        {breadcrumbs.map((crumb, index) => (
          <li key={index} className="flex items-center">
            {index > 0 && (
              <svg className="mx-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            )}

            {crumb.href && !crumb.isActive ? (
              <Link to={crumb.href} className="hover:text-primary transition-colors">
                {crumb.label}
              </Link>
            ) : (
              <span className={crumb.isActive ? 'text-foreground font-medium' : ''}>
                {crumb.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}
