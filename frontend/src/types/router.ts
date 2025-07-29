// Route configuration types for Aperilex
export interface AppRoute {
  id?: string
  path: string
  title?: string
  description?: string
  requiresAuth?: boolean
  breadcrumb?: string
  element?: React.ComponentType
}

export interface RouteData {
  title: string
  description?: string
  breadcrumbs: Array<{
    label: string
    href?: string
  }>
}
