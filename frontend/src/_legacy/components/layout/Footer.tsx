export function Footer() {
  return (
    <footer className="border-t bg-background">
      <div className="container mx-auto px-4 py-4">
        <div className="flex flex-col sm:flex-row justify-between items-center space-y-2 sm:space-y-0">
          {/* Left side: Branding */}
          <div className="flex items-center space-x-4">
            <p className="text-sm text-muted-foreground">
              © 2025 Aperilex. Open-source financial analysis platform.
            </p>
          </div>

        </div>
      </div>
    </footer>
  )
}
