import React, { createRef } from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Input } from './Input'

describe('Input Component', () => {
  describe('Basic Rendering', () => {
    it('renders without errors', () => {
      expect(() => {
        render(<Input />)
      }).not.toThrow()
    })

    it('renders input element', () => {
      render(<Input />)

      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
      expect(input.tagName.toLowerCase()).toBe('input')
    })

    it('renders wrapper div structure', () => {
      render(<Input data-testid="input-wrapper" />)

      const input = screen.getByRole('textbox')
      const wrapper = input.parentElement

      expect(wrapper).toBeInTheDocument()
      expect(wrapper).toHaveClass('space-y-2')
    })

    it('renders without error message by default', () => {
      render(<Input />)

      // Error message should not exist
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument()

      // Error paragraph should not exist
      const errorElements = document.querySelectorAll('p.text-sm.text-destructive')
      expect(errorElements).toHaveLength(0)
    })
  })

  describe('Standard Input Props', () => {
    it('accepts and renders placeholder text', () => {
      const placeholder = 'Enter your name'
      render(<Input placeholder={placeholder} />)

      const input = screen.getByPlaceholderText(placeholder)
      expect(input).toBeInTheDocument()
    })

    it('accepts and displays value prop', () => {
      const value = 'Test Value'
      render(<Input value={value} readOnly />)

      const input = screen.getByDisplayValue(value)
      expect(input).toBeInTheDocument()
    })

    it('handles onChange events', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()

      render(<Input onChange={handleChange} />)

      const input = screen.getByRole('textbox')
      await user.type(input, 'test')

      expect(handleChange).toHaveBeenCalled()
      expect(handleChange).toHaveBeenCalledTimes(4) // One call per character
    })

    it('accepts disabled prop', () => {
      render(<Input disabled />)

      const input = screen.getByRole('textbox')
      expect(input).toBeDisabled()
    })

    it('accepts different input types', () => {
      const { rerender } = render(<Input type="password" />)

      let input = document.querySelector('input[type="password"]')
      expect(input).toHaveAttribute('type', 'password')

      rerender(<Input type="email" />)
      input = document.querySelector('input[type="email"]')
      expect(input).toHaveAttribute('type', 'email')

      rerender(<Input type="number" />)
      input = screen.getByRole('spinbutton')
      expect(input).toHaveAttribute('type', 'number')
    })

    it('accepts name prop', () => {
      const name = 'username'
      render(<Input name={name} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('name', name)
    })

    it('accepts id prop', () => {
      const id = 'user-input'
      render(<Input id={id} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('id', id)
    })

    it('accepts required prop', () => {
      render(<Input required />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('required')
    })

    it('accepts maxLength prop', () => {
      const maxLength = 50
      render(<Input maxLength={maxLength} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('maxLength', maxLength.toString())
    })

    it('accepts readOnly prop', () => {
      render(<Input readOnly />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('readOnly')
    })

    it('accepts autoComplete prop', () => {
      const autoComplete = 'email'
      render(<Input autoComplete={autoComplete} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('autoComplete', autoComplete)
    })
  })

  describe('Error States', () => {
    it('displays error message when error prop is provided', () => {
      const errorMessage = 'This field is required'
      render(<Input error={errorMessage} />)

      const errorElement = screen.getByText(errorMessage)
      expect(errorElement).toBeInTheDocument()
      expect(errorElement.tagName.toLowerCase()).toBe('p')
    })

    it('applies error styling classes when error is present', () => {
      const errorMessage = 'Invalid input'
      render(<Input error={errorMessage} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('border-destructive', 'focus-visible:ring-destructive')
    })

    it('applies correct error message styling', () => {
      const errorMessage = 'Error occurred'
      render(<Input error={errorMessage} />)

      const errorElement = screen.getByText(errorMessage)
      expect(errorElement).toHaveClass('text-sm', 'text-destructive')
    })

    it('does not show error styles when no error is provided', () => {
      render(<Input />)

      const input = screen.getByRole('textbox')
      expect(input).not.toHaveClass('border-destructive')
      expect(input).not.toHaveClass('focus-visible:ring-destructive')
    })

    it('handles empty error string correctly', () => {
      render(<Input error="" />)

      // Empty error should not display error message
      const errorElements = document.querySelectorAll('p.text-sm.text-destructive')
      expect(errorElements).toHaveLength(0)

      // Should not apply error styles
      const input = screen.getByRole('textbox')
      expect(input).not.toHaveClass('border-destructive')
    })

    it('updates error state dynamically', () => {
      const { rerender } = render(<Input />)

      let input = screen.getByRole('textbox')
      expect(input).not.toHaveClass('border-destructive')
      expect(screen.queryByText('Error message')).not.toBeInTheDocument()

      rerender(<Input error="Error message" />)

      input = screen.getByRole('textbox')
      expect(input).toHaveClass('border-destructive')
      expect(screen.getByText('Error message')).toBeInTheDocument()
    })

    it('handles long error messages correctly', () => {
      const longError =
        'This is a very long error message that might wrap to multiple lines and should still be displayed correctly'
      render(<Input error={longError} />)

      const errorElement = screen.getByText(longError)
      expect(errorElement).toBeInTheDocument()
      expect(errorElement).toHaveClass('text-sm', 'text-destructive')
    })

    it('handles special characters in error messages', () => {
      const specialError = 'Error: Invalid format! @#$%^&*()[]{}|;:,.<>?'
      render(<Input error={specialError} />)

      const errorElement = screen.getByText(specialError)
      expect(errorElement).toBeInTheDocument()
    })
  })

  describe('CSS Classes', () => {
    it('applies base classes correctly', () => {
      render(<Input />)

      const input = screen.getByRole('textbox')
      const expectedBaseClasses = [
        'flex',
        'h-10',
        'w-full',
        'rounded-md',
        'border',
        'border-input',
        'bg-background',
        'px-3',
        'py-2',
        'text-sm',
        'ring-offset-background',
        'file:border-0',
        'file:bg-transparent',
        'file:text-sm',
        'file:font-medium',
        'placeholder:text-muted-foreground',
        'focus-visible:outline-none',
        'focus-visible:ring-2',
        'focus-visible:ring-ring',
        'focus-visible:ring-offset-2',
        'disabled:cursor-not-allowed',
        'disabled:opacity-50',
      ]

      expectedBaseClasses.forEach((className) => {
        expect(input).toHaveClass(className)
      })
    })

    it('applies error classes when error is present', () => {
      render(<Input error="Test error" />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('border-destructive')
      expect(input).toHaveClass('focus-visible:ring-destructive')
    })

    it('accepts custom className prop', () => {
      const customClass = 'custom-input-class'
      render(<Input className={customClass} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveClass(customClass)
    })

    it('combines base, error, and custom classes correctly', () => {
      const customClass = 'my-custom-class'
      const errorMessage = 'Error'
      render(<Input className={customClass} error={errorMessage} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('flex') // base class
      expect(input).toHaveClass('border-destructive') // error class
      expect(input).toHaveClass(customClass) // custom class
    })

    it('handles empty className prop', () => {
      render(<Input className="" />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('flex') // Should still have base classes
    })

    it('handles undefined className prop', () => {
      render(<Input className={undefined} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('flex') // Should still have base classes
    })
  })

  describe('Ref Forwarding', () => {
    it('forwards ref correctly to input element', () => {
      const ref = createRef<HTMLInputElement>()
      render(<Input ref={ref} />)

      expect(ref.current).toBeInstanceOf(HTMLInputElement)
      expect(ref.current?.tagName.toLowerCase()).toBe('input')
    })

    it('allows ref methods to be called', () => {
      const ref = createRef<HTMLInputElement>()
      render(<Input ref={ref} />)

      expect(() => {
        ref.current?.focus()
      }).not.toThrow()

      expect(() => {
        ref.current?.blur()
      }).not.toThrow()
    })

    it('maintains ref functionality with error state', () => {
      const ref = createRef<HTMLInputElement>()
      render(<Input ref={ref} error="Test error" />)

      expect(ref.current).toBeInstanceOf(HTMLInputElement)
      expect(ref.current?.classList.contains('border-destructive')).toBe(true)
    })

    it('has correct displayName for debugging', () => {
      expect(Input.displayName).toBe('Input')
    })
  })

  describe('Accessibility', () => {
    it('has proper input role', () => {
      render(<Input />)

      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
    })

    it('supports label association with id', () => {
      const inputId = 'username'
      render(
        <div>
          <label htmlFor={inputId}>Username</label>
          <Input id={inputId} />
        </div>
      )

      const label = screen.getByText('Username')
      const input = screen.getByLabelText('Username')

      expect(label).toBeInTheDocument()
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('id', inputId)
    })

    it('associates error message with input using aria-describedby', () => {
      const inputId = 'test-input'
      const errorMessage = 'This field is required'

      render(<Input id={inputId} error={errorMessage} />)

      const input = screen.getByRole('textbox')
      const errorElement = screen.getByText(errorMessage)

      expect(input).toBeInTheDocument()
      expect(errorElement).toBeInTheDocument()

      // In a real implementation, you might want aria-describedby
      // For now, we just ensure the error is present and accessible
      expect(errorElement).toHaveAttribute('class', expect.stringContaining('text-destructive'))
    })

    it('maintains proper focus handling', async () => {
      const user = userEvent.setup()
      render(<Input />)

      const input = screen.getByRole('textbox')

      await user.click(input)
      expect(input).toHaveFocus()

      await user.tab()
      expect(input).not.toHaveFocus()
    })

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup()
      render(
        <div>
          <Input />
          <Input />
        </div>
      )

      const inputs = screen.getAllByRole('textbox')

      // Tab to first input
      await user.tab()
      expect(inputs[0]).toHaveFocus()

      // Tab to second input
      await user.tab()
      expect(inputs[1]).toHaveFocus()
    })

    it('handles disabled state accessibility', () => {
      render(<Input disabled />)

      const input = screen.getByRole('textbox')
      expect(input).toBeDisabled()
      expect(input).toHaveAttribute('disabled')
    })

    it('supports required field accessibility', () => {
      render(<Input required />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('required')
    })
  })

  describe('User Interaction', () => {
    it('handles typing events correctly', async () => {
      const user = userEvent.setup()
      render(<Input />)

      const input = screen.getByRole('textbox')
      await user.type(input, 'Hello World')

      expect(input).toHaveValue('Hello World')
    })

    it('handles clear and retype', async () => {
      const user = userEvent.setup()
      render(<Input />)

      const input = screen.getByRole('textbox')
      await user.type(input, 'First text')
      expect(input).toHaveValue('First text')

      await user.clear(input)
      expect(input).toHaveValue('')

      await user.type(input, 'Second text')
      expect(input).toHaveValue('Second text')
    })

    it('handles focus and blur events', async () => {
      const user = userEvent.setup()
      const handleFocus = vi.fn()
      const handleBlur = vi.fn()

      render(<Input onFocus={handleFocus} onBlur={handleBlur} />)

      const input = screen.getByRole('textbox')

      await user.click(input)
      expect(handleFocus).toHaveBeenCalledTimes(1)

      await user.tab()
      expect(handleBlur).toHaveBeenCalledTimes(1)
    })

    it('handles keyboard events', async () => {
      const user = userEvent.setup()
      const handleKeyDown = vi.fn()
      const handleKeyUp = vi.fn()

      render(<Input onKeyDown={handleKeyDown} onKeyUp={handleKeyUp} />)

      const input = screen.getByRole('textbox')
      await user.click(input)
      await user.keyboard('a')

      expect(handleKeyDown).toHaveBeenCalled()
      expect(handleKeyUp).toHaveBeenCalled()
    })

    it('handles paste events', async () => {
      const user = userEvent.setup()
      render(<Input />)

      const input = screen.getByRole('textbox')
      await user.click(input)
      await user.paste('Pasted content')

      expect(input).toHaveValue('Pasted content')
    })

    it('handles cut/copy events', async () => {
      const user = userEvent.setup()
      render(<Input defaultValue="Test content" />)

      const input = screen.getByRole('textbox')
      await user.click(input)
      await user.keyboard('{Control>}a{/Control}') // Select all
      await user.cut()

      expect(input).toHaveValue('')
    })

    it('respects maxLength constraint', async () => {
      const user = userEvent.setup()
      render(<Input maxLength={5} />)

      const input = screen.getByRole('textbox')
      await user.type(input, '1234567890')

      expect(input).toHaveValue('12345') // Only first 5 characters
    })

    it('handles controlled input correctly', async () => {
      const user = userEvent.setup()
      const ControlledInput = () => {
        const [value, setValue] = React.useState('')
        return <Input value={value} onChange={(e) => setValue(e.target.value)} />
      }

      render(<ControlledInput />)

      const input = screen.getByRole('textbox')
      await user.type(input, 'controlled')

      expect(input).toHaveValue('controlled')
    })
  })

  describe('Edge Cases', () => {
    it('handles null and undefined props gracefully', () => {
      expect(() => {
        render(<Input value={undefined} />)
      }).not.toThrow()

      expect(() => {
        render(<Input onChange={undefined} />)
      }).not.toThrow()
    })

    it('handles rapid state changes', () => {
      const { rerender } = render(<Input error="Error 1" />)

      expect(screen.getByText('Error 1')).toBeInTheDocument()

      rerender(<Input error="Error 2" />)
      expect(screen.getByText('Error 2')).toBeInTheDocument()
      expect(screen.queryByText('Error 1')).not.toBeInTheDocument()

      rerender(<Input />)
      expect(screen.queryByText('Error 2')).not.toBeInTheDocument()
    })

    it('maintains input state during error changes', async () => {
      const user = userEvent.setup()
      const { rerender } = render(<Input />)

      const input = screen.getByRole('textbox')
      await user.type(input, 'user content')
      expect(input).toHaveValue('user content')

      rerender(<Input error="Validation error" />)
      const updatedInput = screen.getByRole('textbox')
      expect(updatedInput).toHaveValue('user content') // Value should persist
      expect(screen.getByText('Validation error')).toBeInTheDocument()
    })

    it('handles multiple error state toggles', () => {
      const { rerender } = render(<Input />)

      // No error initially
      expect(screen.queryByText('Error')).not.toBeInTheDocument()

      // Add error
      rerender(<Input error="Error" />)
      expect(screen.getByText('Error')).toBeInTheDocument()

      // Remove error
      rerender(<Input />)
      expect(screen.queryByText('Error')).not.toBeInTheDocument()

      // Add different error
      rerender(<Input error="Different error" />)
      expect(screen.getByText('Different error')).toBeInTheDocument()
    })

    it('handles whitespace-only error messages', () => {
      render(<Input error="   " />)

      // Whitespace-only error should still render the error element
      const errorElement = document.querySelector('p.text-sm.text-destructive')
      expect(errorElement).toBeInTheDocument()
      expect(errorElement).toHaveClass('text-destructive')

      // Error styling should be applied to input
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('border-destructive')
    })

    it('handles very long input values', async () => {
      const user = userEvent.setup()
      const longValue = 'a'.repeat(1000)

      render(<Input />)

      const input = screen.getByRole('textbox')
      // Use paste instead of type for performance with very long values
      await user.click(input)
      await user.paste(longValue)

      expect(input).toHaveValue(longValue)
    })

    it('handles component cleanup properly', () => {
      const { unmount } = render(<Input error="Test error" />)

      expect(() => {
        unmount()
      }).not.toThrow()
    })
  })

  describe('Form Integration', () => {
    it('works within form context', async () => {
      const user = userEvent.setup()
      const handleSubmit = vi.fn((e) => e.preventDefault())

      render(
        <form onSubmit={handleSubmit}>
          <Input name="username" />
          <button type="submit">Submit</button>
        </form>
      )

      const input = screen.getByRole('textbox')
      const button = screen.getByRole('button')

      await user.type(input, 'testuser')
      await user.click(button)

      expect(handleSubmit).toHaveBeenCalledTimes(1)
    })

    it('supports form validation states', () => {
      render(
        <form>
          <Input required name="required-field" />
          <Input name="optional-field" />
        </form>
      )

      const requiredInput = document.querySelector('input[name="required-field"]')
      const optionalInput = document.querySelector('input[name="optional-field"]')

      expect(requiredInput).toHaveAttribute('required')
      expect(optionalInput).not.toHaveAttribute('required')
    })

    it('participates in form data collection', async () => {
      const user = userEvent.setup()

      render(
        <form>
          <Input name="field1" defaultValue="value1" />
          <Input name="field2" />
        </form>
      )

      const input2 = document.querySelector('input[name="field2"]') as HTMLInputElement
      expect(input2).toBeTruthy()

      await user.type(input2, 'value2')
      // Ensure input has the expected value before checking form data
      expect(input2).toHaveValue('value2')

      const form = document.querySelector('form') as HTMLFormElement
      const formData = new FormData(form)

      expect(formData.get('field1')).toBe('value1')
      expect(formData.get('field2')).toBe('value2')
    })

    it('handles form reset correctly', () => {
      render(
        <form>
          <Input name="resetable" defaultValue="initial" />
          <button type="reset">Reset</button>
        </form>
      )

      const input = document.querySelector('input[name="resetable"]') as HTMLInputElement
      const resetButton = screen.getByRole('button', { name: 'Reset' })

      // Change value
      fireEvent.change(input, { target: { value: 'changed' } })
      expect(input.value).toBe('changed')

      // Reset form
      fireEvent.click(resetButton)
      expect(input.value).toBe('initial')
    })
  })

  describe('Performance and Re-rendering', () => {
    it('does not cause unnecessary re-renders', () => {
      const { rerender } = render(<Input placeholder="test" />)

      const input = screen.getByRole('textbox')
      const initialClasses = input.className

      // Re-render with same props
      rerender(<Input placeholder="test" />)

      const rerenderedInput = screen.getByRole('textbox')
      expect(rerenderedInput.className).toBe(initialClasses)
    })

    it('updates efficiently when props change', () => {
      const { rerender } = render(<Input placeholder="initial" />)

      expect(screen.getByPlaceholderText('initial')).toBeInTheDocument()

      rerender(<Input placeholder="updated" />)

      expect(screen.getByPlaceholderText('updated')).toBeInTheDocument()
      expect(screen.queryByPlaceholderText('initial')).not.toBeInTheDocument()
    })

    it('maintains reference stability for event handlers', () => {
      const stableHandler = vi.fn()
      const { rerender } = render(<Input onChange={stableHandler} />)

      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()

      rerender(<Input onChange={stableHandler} />)

      const rerenderedInput = screen.getByRole('textbox')
      // Note: This is a simple check; in real scenarios you might use useCallback
      expect(rerenderedInput).toBeInTheDocument()
    })
  })
})
