import { useState } from 'react'
import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/Button'

export function UserPreferences() {
  const { theme, setTheme, preferences, updatePreferences } = useAppStore()
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const toggleDropdown = () => setDropdownOpen(!dropdownOpen)

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme)
    setDropdownOpen(false)
  }

  return (
    <div className="relative">
      <Button variant="ghost" size="sm" onClick={toggleDropdown}>
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      </Button>

      {dropdownOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setDropdownOpen(false)} />

          {/* Dropdown */}
          <div className="absolute right-0 z-20 mt-2 w-56 rounded-md border bg-background p-2 shadow-lg">
            <div className="space-y-1">
              <div className="px-2 py-1.5">
                <div className="text-sm font-semibold">Preferences</div>
              </div>

              <hr className="my-1" />

              {/* Theme Selection */}
              <div className="px-2 py-1">
                <div className="text-xs font-semibold text-muted-foreground mb-2">THEME</div>

                <div className="space-y-1">
                  {(['light', 'dark', 'system'] as const).map((themeOption) => (
                    <button
                      key={themeOption}
                      onClick={() => handleThemeChange(themeOption)}
                      className={`
                        w-full flex items-center space-x-2 rounded-md px-2 py-1.5 text-sm
                        ${
                          theme === themeOption
                            ? 'bg-accent text-accent-foreground'
                            : 'hover:bg-accent hover:text-accent-foreground'
                        }
                      `}
                    >
                      <div className="w-3 h-3 rounded-full border-2 border-current">
                        {theme === themeOption && (
                          <div className="w-full h-full rounded-full bg-current scale-50"></div>
                        )}
                      </div>
                      <span className="capitalize">{themeOption}</span>
                    </button>
                  ))}
                </div>
              </div>

              <hr className="my-1" />

              {/* Other Preferences */}
              <div className="px-2 py-1">
                <div className="text-xs font-semibold text-muted-foreground mb-2">DISPLAY</div>

                <label className="flex items-center space-x-2 py-1">
                  <input
                    type="checkbox"
                    checked={preferences.compactMode}
                    onChange={(e) => updatePreferences({ compactMode: e.target.checked })}
                    className="rounded border-input"
                  />
                  <span className="text-sm">Compact mode</span>
                </label>

                <label className="flex items-center space-x-2 py-1">
                  <input
                    type="checkbox"
                    checked={preferences.enableNotifications}
                    onChange={(e) => updatePreferences({ enableNotifications: e.target.checked })}
                    className="rounded border-input"
                  />
                  <span className="text-sm">Enable notifications</span>
                </label>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
