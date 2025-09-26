export function MarketOverview() {
  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">Market Overview</h2>

      <div className="space-y-4">
        {/* Market Stats Placeholder */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">+2.3%</div>
            <div className="text-xs text-muted-foreground">S&P 500</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">+1.8%</div>
            <div className="text-xs text-muted-foreground">NASDAQ</div>
          </div>
        </div>

        {/* <hr /> */}

        {/* Recent Filings */}
        {/* <div>
          <h3 className="text-sm font-semibold mb-2">Recent SEC Filings</h3>
          <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">AAPL 10-K</span>
              <span className="text-xs text-muted-foreground">2h ago</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">GOOGL 10-Q</span>
              <span className="text-xs text-muted-foreground">4h ago</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">MSFT 8-K</span>
              <span className="text-xs text-muted-foreground">6h ago</span>
            </div>
          </div>
        </div>

        <hr /> */}

        {/* Analysis Stats */}
        {/* <div>
          <h3 className="text-sm font-semibold mb-2">Today's Activity</h3>
          <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span>Analyses completed</span>
              <span className="font-semibold">0</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span>Filings processed</span>
              <span className="font-semibold">0</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span>Companies analyzed</span>
              <span className="font-semibold">0</span>
            </div>
          </div>
        </div> */}
      </div>
    </div>
  )
}
