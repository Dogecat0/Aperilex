import React from 'react'
import type { LucideIcon } from 'lucide-react'

interface CardProps {
  className?: string
  children: React.ReactNode
}

export function Card({ className = '', children }: CardProps) {
  return (
    <div className={`bg-card rounded-lg border border-border shadow-sm ${className}`}>
      {children}
    </div>
  )
}

interface CardHeaderProps {
  className?: string
  children: React.ReactNode
}

export function CardHeader({ className = '', children }: CardHeaderProps) {
  return <div className={`px-6 py-4 border-b border-border ${className}`}>{children}</div>
}

interface CardContentProps {
  className?: string
  children: React.ReactNode
}

export function CardContent({ className = '', children }: CardContentProps) {
  return <div className={`px-6 py-4 ${className}`}>{children}</div>
}

interface CardTitleProps {
  className?: string
  children: React.ReactNode
}

export function CardTitle({ className = '', children }: CardTitleProps) {
  return <h3 className={`text-lg font-semibold text-foreground ${className}`}>{children}</h3>
}

interface CardDescriptionProps {
  className?: string
  children: React.ReactNode
}

export function CardDescription({ className = '', children }: CardDescriptionProps) {
  return <p className={`text-sm text-muted-foreground mt-1 ${className}`}>{children}</p>
}

interface IconCardProps {
  icon: LucideIcon
  title: string
  description?: string
  children?: React.ReactNode
  className?: string
  iconColor?: string
}

export function IconCard({
  icon: Icon,
  title,
  description,
  children,
  className = '',
  iconColor = 'text-primary bg-primary/10',
}: IconCardProps) {
  return (
    <Card className={`hover:shadow-md transition-shadow ${className}`}>
      <CardContent>
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${iconColor} flex-shrink-0`}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base">{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
            {children && <div className="mt-3">{children}</div>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
