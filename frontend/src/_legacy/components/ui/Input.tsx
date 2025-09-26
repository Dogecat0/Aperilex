import type { InputHTMLAttributes } from 'react'
import { forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', error, ...props }, ref) => {
    const baseClasses =
      'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50'

    const errorClasses = error ? 'border-destructive focus-visible:ring-destructive' : ''

    const classes = `${baseClasses} ${errorClasses} ${className}`

    return (
      <div className="space-y-2">
        <input className={classes} ref={ref} {...props} />
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'
