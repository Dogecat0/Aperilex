import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Skeleton } from './Skeleton'

describe('Skeleton', () => {
  describe('Basic Rendering', () => {
    it('renders without errors', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toBeInTheDocument()
    })

    it('renders as a div element', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton.tagName).toBe('DIV')
    })

    it('renders with default classes when no className provided', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted')
    })
  })

  describe('CSS Classes', () => {
    it('applies base animation classes', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('applies base styling classes', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('rounded-md', 'bg-muted')
    })

    it('merges custom className with base classes', () => {
      const { container } = render(<Skeleton className="h-4 w-full" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted', 'h-4', 'w-full')
    })

    it('handles multiple custom classes', () => {
      const { container } = render(<Skeleton className="h-8 w-32 mb-2 mx-auto" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass(
        'animate-pulse',
        'rounded-md',
        'bg-muted',
        'h-8',
        'w-32',
        'mb-2',
        'mx-auto'
      )
    })

    it('preserves all base classes when custom className is provided', () => {
      const { container } = render(<Skeleton className="custom-class" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse')
      expect(skeleton).toHaveClass('rounded-md')
      expect(skeleton).toHaveClass('bg-muted')
      expect(skeleton).toHaveClass('custom-class')
    })
  })

  describe('Props Handling', () => {
    it('handles className prop correctly', () => {
      const { container } = render(<Skeleton className="test-class" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('test-class')
    })

    it('handles empty className string', () => {
      const { container } = render(<Skeleton className="" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted')
      expect(skeleton.className).toBe('animate-pulse rounded-md bg-muted ')
    })

    it('handles undefined className (default behavior)', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted')
    })

    it('handles whitespace in className', () => {
      const { container } = render(<Skeleton className="  spaced-class  " />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted')
      expect(skeleton.className).toContain('spaced-class')
    })
  })

  describe('Animation', () => {
    it('has animate-pulse class for loading animation', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('maintains animate-pulse class with custom className', () => {
      const { container } = render(<Skeleton className="h-4 w-full bg-gray-200" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse')
    })
  })

  describe('Styling', () => {
    it('has rounded-md class for border radius', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('rounded-md')
    })

    it('has bg-muted class for background color', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('bg-muted')
    })

    it('maintains base styling with custom background classes', () => {
      const { container } = render(<Skeleton className="bg-gray-300" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('rounded-md', 'bg-muted', 'bg-gray-300')
    })
  })

  describe('Edge Cases', () => {
    it('handles long className strings', () => {
      const longClassName =
        'h-4 w-full bg-gray-200 rounded-lg animate-bounce shadow-md border-2 border-gray-300 mb-4 mt-2 mx-auto px-4 py-2 text-center font-bold text-lg leading-tight tracking-wide'
      const { container } = render(<Skeleton className={longClassName} />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted')
      expect(skeleton.className).toContain(longClassName)
    })

    it('handles special characters in className', () => {
      const { container } = render(<Skeleton className="test-class_with-special.chars:hover" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted')
      expect(skeleton.className).toContain('test-class_with-special.chars:hover')
    })

    it('handles className with numbers', () => {
      const { container } = render(<Skeleton className="h-4 w-1/2 mb-2 p-4 text-xl" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass(
        'animate-pulse',
        'rounded-md',
        'bg-muted',
        'h-4',
        'w-1/2',
        'mb-2',
        'p-4',
        'text-xl'
      )
    })

    it('handles duplicate classes gracefully', () => {
      const { container } = render(<Skeleton className="animate-pulse rounded-md bg-muted" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted')
    })
  })

  describe('Accessibility', () => {
    it('does not have any accessibility violations for loading states', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toBeInTheDocument()
      expect(skeleton).not.toHaveAttribute('aria-hidden', 'false')
    })

    it('can be identified by container and class selector', () => {
      const { container } = render(<Skeleton className="custom-skeleton-class" />)
      const skeleton = container.querySelector('.custom-skeleton-class')
      expect(skeleton).toBeInTheDocument()
      expect(skeleton).toHaveClass(
        'animate-pulse',
        'rounded-md',
        'bg-muted',
        'custom-skeleton-class'
      )
    })

    it('does not interfere with screen readers by default', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).not.toHaveAttribute('role', 'presentation')
      expect(skeleton).not.toHaveAttribute('aria-label')
    })
  })

  describe('Multiple Instances', () => {
    it('can render multiple skeletons without conflicts', () => {
      const { container } = render(
        <div>
          <Skeleton className="h-4 w-full mb-2" />
          <Skeleton className="h-4 w-3/4 mb-2" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      )

      const skeletons = container.querySelectorAll('.animate-pulse')
      expect(skeletons).toHaveLength(3)

      skeletons.forEach((skeleton) => {
        expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted')
      })
    })

    it('maintains individual className for each skeleton', () => {
      const { container } = render(
        <div>
          <Skeleton className="h-4 skeleton-1" />
          <Skeleton className="h-8 skeleton-2" />
          <Skeleton className="h-12 skeleton-3" />
        </div>
      )

      const skeleton1 = container.querySelector('.skeleton-1')
      const skeleton2 = container.querySelector('.skeleton-2')
      const skeleton3 = container.querySelector('.skeleton-3')

      expect(skeleton1).toHaveClass('h-4', 'skeleton-1')
      expect(skeleton2).toHaveClass('h-8', 'skeleton-2')
      expect(skeleton3).toHaveClass('h-12', 'skeleton-3')
    })

    it('renders skeleton list correctly', () => {
      const skeletonCount = 5
      const { container } = render(
        <div>
          {Array.from({ length: skeletonCount }, (_, index) => (
            <Skeleton key={index} className={`h-4 mb-2 skeleton-${index}`} />
          ))}
        </div>
      )

      const skeletons = container.querySelectorAll('.animate-pulse')
      expect(skeletons).toHaveLength(skeletonCount)

      skeletons.forEach((skeleton, index) => {
        expect(skeleton).toHaveClass(
          'animate-pulse',
          'rounded-md',
          'bg-muted',
          'h-4',
          'mb-2',
          `skeleton-${index}`
        )
      })
    })
  })

  describe('Component Interface', () => {
    it('accepts only className prop as per interface', () => {
      // This test ensures the component interface is correctly implemented
      const component = <Skeleton className="test" />
      expect(component.props.className).toBe('test')
    })

    it('defaults className to empty string as per implementation', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement
      // The implementation uses className = '' as default, which results in trailing space
      expect(skeleton.className).toBe('animate-pulse rounded-md bg-muted ')
    })
  })

  describe('Real-world Usage Scenarios', () => {
    it('works as text line skeleton', () => {
      const { container } = render(<Skeleton className="h-4 w-full" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted', 'h-4', 'w-full')
    })

    it('works as avatar skeleton', () => {
      const { container } = render(<Skeleton className="h-12 w-12 rounded-full" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass(
        'animate-pulse',
        'rounded-md',
        'bg-muted',
        'h-12',
        'w-12',
        'rounded-full'
      )
    })

    it('works as card skeleton', () => {
      const { container } = render(<Skeleton className="h-32 w-full rounded-lg" />)
      const skeleton = container.firstChild as HTMLElement
      expect(skeleton).toHaveClass(
        'animate-pulse',
        'rounded-md',
        'bg-muted',
        'h-32',
        'w-full',
        'rounded-lg'
      )
    })

    it('works in skeleton content layout', () => {
      const { container } = render(
        <div className="space-y-3">
          <Skeleton className="h-5 w-2/5" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/5" />
        </div>
      )

      const skeletons = container.querySelectorAll('.animate-pulse')
      expect(skeletons).toHaveLength(3)
      expect(skeletons[0]).toHaveClass('h-5', 'w-2/5')
      expect(skeletons[1]).toHaveClass('h-4', 'w-4/5')
      expect(skeletons[2]).toHaveClass('h-4', 'w-3/5')
    })
  })
})
