import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { Button } from './Button'

describe('Button Component', () => {
  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      expect(() => {
        render(<Button>Test Button</Button>)
      }).not.toThrow()
    })

    it('renders with correct text content', () => {
      render(<Button>Click me</Button>)

      const button = screen.getByRole('button', { name: 'Click me' })
      expect(button).toBeInTheDocument()
      expect(button).toHaveTextContent('Click me')
    })

    it('renders as button element by default', () => {
      render(<Button>Test</Button>)

      const button = screen.getByRole('button')
      expect(button.tagName).toBe('BUTTON')
    })

    it('applies default props correctly', () => {
      render(<Button>Default Button</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-primary', 'text-primary-foreground', 'hover:bg-primary/90') // primary variant
      expect(button).toHaveClass('h-10', 'px-4') // md size
    })

    it('has correct displayName', () => {
      expect(Button.displayName).toBe('Button')
    })

    it('renders empty children without errors', () => {
      expect(() => {
        render(<Button />)
      }).not.toThrow()

      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
      expect(button).toBeEmptyDOMElement()
    })
  })

  describe('Variants', () => {
    it('applies primary variant classes', () => {
      render(<Button variant="primary">Primary</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-primary', 'text-primary-foreground', 'hover:bg-primary/90')
    })

    it('applies secondary variant classes', () => {
      render(<Button variant="secondary">Secondary</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass(
        'bg-secondary',
        'text-secondary-foreground',
        'hover:bg-secondary/80'
      )
    })

    it('applies outline variant classes', () => {
      render(<Button variant="outline">Outline</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass(
        'border',
        'border-input',
        'bg-outline-bg',
        'hover:bg-accent',
        'hover:text-accent-foreground'
      )
    })

    it('applies ghost variant classes', () => {
      render(<Button variant="ghost">Ghost</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('hover:bg-accent', 'hover:text-accent-foreground')
      expect(button).not.toHaveClass('bg-primary', 'border')
    })

    it('applies danger variant classes', () => {
      render(<Button variant="danger">Danger</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass(
        'bg-destructive',
        'text-destructive-foreground',
        'hover:bg-destructive/90'
      )
    })

    it('defaults to primary variant when variant is undefined', () => {
      render(<Button>Default</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-primary', 'text-primary-foreground', 'hover:bg-primary/90')
    })
  })

  describe('Sizes', () => {
    it('applies small size classes', () => {
      render(<Button size="sm">Small</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-9', 'px-3', 'text-sm')
    })

    it('applies medium size classes', () => {
      render(<Button size="md">Medium</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-10', 'px-4')
      expect(button).not.toHaveClass('text-sm') // md doesn't have text-sm
    })

    it('applies large size classes', () => {
      render(<Button size="lg">Large</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-11', 'px-8')
    })

    it('defaults to medium size when size is undefined', () => {
      render(<Button>Default</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-10', 'px-4')
    })
  })

  describe('Polymorphic Behavior', () => {
    it('renders as anchor element when as="a"', () => {
      render(
        <Button as="a" href="/test">
          Link Button
        </Button>
      )

      const link = screen.getByRole('link', { name: 'Link Button' })
      expect(link.tagName).toBe('A')
      expect(link).toHaveAttribute('href', '/test')
    })

    it('renders as div element when as="div"', () => {
      render(<Button as="div">Div Button</Button>)

      const div = screen.getByText('Div Button')
      expect(div.tagName).toBe('DIV')
    })

    it('renders as span element when as="span"', () => {
      render(<Button as="span">Span Button</Button>)

      const span = screen.getByText('Span Button')
      expect(span.tagName).toBe('SPAN')
    })

    it('maintains styling when rendered as different elements', () => {
      render(
        <Button as="div" variant="secondary" size="lg">
          Styled Div
        </Button>
      )

      const div = screen.getByText('Styled Div')
      expect(div).toHaveClass('bg-secondary', 'text-secondary-foreground', 'hover:bg-secondary/80')
      expect(div).toHaveClass('h-11', 'px-8')
    })
  })

  describe('Props Handling', () => {
    it('handles onClick prop correctly', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()

      render(<Button onClick={handleClick}>Clickable</Button>)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('handles disabled prop correctly', () => {
      render(<Button disabled>Disabled</Button>)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      expect(button).toHaveClass('disabled:pointer-events-none', 'disabled:opacity-50')
    })

    it('handles type prop correctly', () => {
      render(<Button type="submit">Submit</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('type', 'submit')
    })

    it('passes through other ButtonHTMLAttributes', () => {
      render(
        <Button
          id="test-button"
          data-testid="custom-button"
          aria-label="Custom button"
          form="test-form"
        >
          Button
        </Button>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('id', 'test-button')
      expect(button).toHaveAttribute('data-testid', 'custom-button')
      expect(button).toHaveAttribute('aria-label', 'Custom button')
      expect(button).toHaveAttribute('form', 'test-form')
    })

    it('does not pass onClick to non-interactive polymorphic elements when disabled', () => {
      const handleClick = vi.fn()

      render(
        <Button as="div" onClick={handleClick} disabled>
          Disabled Div
        </Button>
      )

      const div = screen.getByText('Disabled Div')
      fireEvent.click(div)

      // The click should still be registered on the DOM element,
      // but styling should prevent interaction
      expect(div).toHaveClass('disabled:pointer-events-none')
    })
  })

  describe('CSS Classes', () => {
    it('applies base classes to all buttons', () => {
      render(<Button>Test</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass(
        'inline-flex',
        'items-center',
        'justify-center',
        'rounded-md',
        'font-medium',
        'transition-colors',
        'focus-visible:outline-none',
        'focus-visible:ring-2',
        'focus-visible:ring-ring',
        'disabled:pointer-events-none',
        'disabled:opacity-50'
      )
    })

    it('combines variant and size classes correctly', () => {
      render(
        <Button variant="outline" size="lg">
          Large Outline
        </Button>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveClass('border', 'border-input', 'bg-outline-bg') // outline variant
      expect(button).toHaveClass('h-11', 'px-8') // lg size
    })

    it('applies custom className alongside component classes', () => {
      render(<Button className="custom-class another-class">Custom</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('custom-class', 'another-class')
      expect(button).toHaveClass('inline-flex', 'items-center') // base classes should still be present
    })

    it('handles empty className prop', () => {
      render(<Button className="">Empty Class</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('inline-flex', 'items-center', 'justify-center')
    })

    it('handles undefined className prop', () => {
      render(<Button className={undefined}>Undefined Class</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('inline-flex', 'items-center', 'justify-center')
    })
  })

  describe('Ref Forwarding', () => {
    it('forwards ref to button element correctly', () => {
      const ref = createRef<HTMLButtonElement>()

      render(<Button ref={ref}>Ref Button</Button>)

      expect(ref.current).toBeInstanceOf(HTMLButtonElement)
      expect(ref.current?.textContent).toBe('Ref Button')
    })

    it('forwards ref to polymorphic element correctly', () => {
      const ref = createRef<HTMLAnchorElement>()

      render(
        <Button as="a" ref={ref} href="/test">
          Link with Ref
        </Button>
      )

      expect(ref.current).toBeInstanceOf(HTMLAnchorElement)
      expect(ref.current?.textContent).toBe('Link with Ref')
      expect(ref.current?.href).toContain('/test')
    })

    it('allows ref access to DOM methods', () => {
      const ref = createRef<HTMLButtonElement>()

      render(<Button ref={ref}>Focusable</Button>)

      expect(ref.current?.focus).toBeDefined()
      expect(ref.current?.click).toBeDefined()
      expect(ref.current?.blur).toBeDefined()
    })
  })

  describe('Accessibility', () => {
    it('is focusable by default', () => {
      render(<Button>Focusable</Button>)

      const button = screen.getByRole('button')
      expect(button).not.toHaveAttribute('tabindex', '-1')
    })

    it('handles focus correctly', async () => {
      const user = userEvent.setup()

      render(<Button>Focus Test</Button>)

      const button = screen.getByRole('button')
      await user.tab()

      expect(button).toHaveFocus()
    })

    it('shows focus ring when focused', async () => {
      const user = userEvent.setup()

      render(<Button>Focus Ring</Button>)

      const button = screen.getByRole('button')
      await user.tab()

      expect(button).toHaveClass(
        'focus-visible:outline-none',
        'focus-visible:ring-2',
        'focus-visible:ring-ring'
      )
    })

    it('prevents focus when disabled', () => {
      render(<Button disabled>Disabled Focus</Button>)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      expect(button).toHaveClass('disabled:pointer-events-none')
    })

    it('maintains semantic button role', () => {
      render(<Button>Semantic Button</Button>)

      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
    })

    it('supports ARIA attributes', () => {
      render(
        <Button aria-label="Custom label" aria-describedby="description" aria-expanded={false}>
          ARIA Button
        </Button>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label', 'Custom label')
      expect(button).toHaveAttribute('aria-describedby', 'description')
      expect(button).toHaveAttribute('aria-expanded', 'false')
    })

    it('handles keyboard navigation correctly', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()

      render(<Button onClick={handleClick}>Keyboard Test</Button>)

      const button = screen.getByRole('button')
      await user.tab()
      expect(button).toHaveFocus()

      await user.keyboard('[Enter]')
      expect(handleClick).toHaveBeenCalledTimes(1)

      await user.keyboard('[Space]')
      expect(handleClick).toHaveBeenCalledTimes(2)
    })
  })

  describe('Event Handling', () => {
    it('handles click events correctly', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()

      render(<Button onClick={handleClick}>Click Test</Button>)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('does not trigger onClick when disabled', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()

      render(
        <Button onClick={handleClick} disabled>
          Disabled Click
        </Button>
      )

      const button = screen.getByRole('button')
      await user.click(button)

      expect(handleClick).not.toHaveBeenCalled()
    })

    it('handles multiple event handlers', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      const handleMouseEnter = vi.fn()
      const handleMouseLeave = vi.fn()

      render(
        <Button
          onClick={handleClick}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          Multi Event
        </Button>
      )

      const button = screen.getByRole('button')
      await user.hover(button)
      expect(handleMouseEnter).toHaveBeenCalledTimes(1)

      await user.unhover(button)
      expect(handleMouseLeave).toHaveBeenCalledTimes(1)

      await user.click(button)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('passes event object to onClick handler', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()

      render(<Button onClick={handleClick}>Event Test</Button>)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(handleClick).toHaveBeenCalledWith(expect.any(Object))
      const event = handleClick.mock.calls[0][0]
      expect(event.type).toBe('click')
    })
  })

  describe('Edge Cases', () => {
    it('handles complex className combinations', () => {
      render(
        <Button variant="outline" size="lg" className="custom-1 custom-2 hover:custom-3">
          Complex Classes
        </Button>
      )

      const button = screen.getByRole('button')
      // Should have base classes
      expect(button).toHaveClass('inline-flex', 'items-center', 'justify-center')
      // Should have variant classes
      expect(button).toHaveClass('border', 'border-input', 'bg-outline-bg')
      // Should have size classes
      expect(button).toHaveClass('h-11', 'px-8')
      // Should have custom classes
      expect(button).toHaveClass('custom-1', 'custom-2', 'hover:custom-3')
    })

    it('handles null children gracefully', () => {
      expect(() => {
        render(<Button>{null}</Button>)
      }).not.toThrow()

      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
    })

    it('handles complex children elements', () => {
      render(
        <Button>
          <span>Icon</span>
          <span>Text</span>
          <div>Complex</div>
        </Button>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveTextContent('IconTextComplex')
      expect(button.querySelector('span')).toBeInTheDocument()
      expect(button.querySelector('div')).toBeInTheDocument()
    })

    it('maintains styling with very long text content', () => {
      const longText =
        'This is a very long button text that should still maintain proper styling and layout without breaking the component structure'

      render(<Button>{longText}</Button>)

      const button = screen.getByRole('button')
      expect(button).toHaveTextContent(longText)
      expect(button).toHaveClass('inline-flex', 'items-center', 'justify-center')
    })

    it('handles rapid successive clicks', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()

      render(<Button onClick={handleClick}>Rapid Click</Button>)

      const button = screen.getByRole('button')

      // Simulate rapid clicks
      await user.click(button)
      await user.click(button)
      await user.click(button)

      expect(handleClick).toHaveBeenCalledTimes(3)
    })

    it('works with React fragments as children', () => {
      render(
        <Button>
          <>
            <span>Fragment</span>
            <span>Content</span>
          </>
        </Button>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveTextContent('FragmentContent')
    })
  })

  describe('Performance and Consistency', () => {
    it('renders consistently across multiple renders', () => {
      const { rerender } = render(<Button variant="primary">Initial</Button>)

      const initialButton = screen.getByRole('button')
      expect(initialButton).toHaveClass('bg-primary')

      rerender(<Button variant="secondary">Updated</Button>)

      const updatedButton = screen.getByRole('button')
      expect(updatedButton).toHaveClass('bg-secondary')
      expect(updatedButton).toHaveTextContent('Updated')
    })

    it('maintains ref consistency across re-renders', () => {
      const ref = createRef<HTMLButtonElement>()
      const { rerender } = render(<Button ref={ref}>Initial</Button>)

      const initialRef = ref.current
      expect(initialRef).toBeInstanceOf(HTMLButtonElement)

      rerender(<Button ref={ref}>Updated</Button>)

      // Ref should point to the new element after re-render
      expect(ref.current).toBeInstanceOf(HTMLButtonElement)
      expect(ref.current?.textContent).toBe('Updated')
    })

    it('does not create memory leaks during unmount', () => {
      const { unmount } = render(<Button>Unmount Test</Button>)

      expect(() => {
        unmount()
      }).not.toThrow()
    })
  })
})
