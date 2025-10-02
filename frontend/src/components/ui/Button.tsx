import { forwardRef, useMemo } from 'react'
import type { ButtonHTMLAttributes, CSSProperties } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive'
export type ButtonSize = 'sm' | 'md'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', className = '', style, ...props },
  ref
) {
  const tokens = useThemeTokens()

  const palette = useMemo(() => {
    switch (variant) {
      case 'secondary':
        return {
          background: tokens.surfaces.raised,
          color: tokens.text.primary,
          border: tokens.lines.subtle,
          shadow: 'none',
        }
      case 'ghost':
        return {
          background: 'transparent',
          color: tokens.text.secondary,
          border: 'transparent',
          shadow: 'none',
        }
      case 'destructive':
        return {
          background: tokens.status.negative,
          color: tokens.text.onBrand,
          border: tokens.status.negative,
          shadow: tokens.shadows.soft,
        }
      case 'primary':
      default:
        return {
          background: tokens.action.primary,
          color: tokens.action.primaryContrast ?? tokens.text.onBrand,
          border: tokens.action.primary,
          shadow: tokens.shadows.soft,
        }
    }
  }, [tokens, variant])

  const baseClass =
    'inline-flex items-center justify-center rounded-full border font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60'
  let variantClass = 'hover:brightness-[0.95] active:brightness-[0.9]'
  if (variant === 'ghost') {
    variantClass = 'hover:underline'
  }

  let sizeClass = 'px-5 py-3 text-sm'
  if (size === 'sm') {
    sizeClass = 'px-4 py-2 text-xs uppercase tracking-[0.2em]'
  }

  const finalClass = [baseClass, variantClass, sizeClass, className].filter(Boolean).join(' ')

  const finalStyle: CSSProperties = {
    background: palette.background,
    color: palette.color,
    borderColor: palette.border,
    boxShadow: palette.shadow,
    outlineColor: tokens.focus.ring,
    transition: [
      'background-color 150ms ease',
      'color 150ms ease',
      'box-shadow 150ms ease',
      'filter 150ms ease',
    ].join(', '),
    ...style,
  }

  return <button ref={ref} className={finalClass} style={finalStyle} {...props} />
})
