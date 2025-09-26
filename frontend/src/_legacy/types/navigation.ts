import type { ReactNode } from 'react'

export interface BreadcrumbItem {
  label: string
  href?: string
  isActive?: boolean
}

export interface NavigationItem {
  id: string
  label: string
  href: string
  icon?: ReactNode
  badge?: string | number
  children?: NavigationItem[]
}
