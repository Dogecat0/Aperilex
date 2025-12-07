import { useEffect, useState } from 'react'

type HeroGraphicProps = {
  activeSlideId: string
}

export function HeroGraphic({ activeSlideId }: HeroGraphicProps) {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    switch (activeSlideId) {
      case 'launchpad-intake':
        setStage(1)
        break
      case 'dashboard-rollup':
        setStage(2)
        break
      case 'saved-drawer':
        setStage(3)
        break
      default:
        setStage(1)
    }
  }, [activeSlideId])

  return (
    <div className="relative w-full h-[400px] flex items-center justify-center overflow-hidden rounded-[40px] border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)]/40 backdrop-blur-xl shadow-2xl">
      {/* Background Grid */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, var(--text-secondary) 1px, transparent 0)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Main SVG Scene */}
      <svg
        className="w-full h-full max-w-[500px]"
        viewBox="0 0 500 400"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* --- STAGE 1: THE MAP (Launchpad) --- */}
        <g
          className={`transition-all duration-700 ${stage === 1 ? 'opacity-100' : 'opacity-20 blur-sm'}`}
        >
          {/* Document Outline */}
          <rect
            x="150"
            y="50"
            width="200"
            height="300"
            rx="8"
            fill="var(--surfaces-base)"
            stroke="var(--lines-subtle)"
            strokeWidth="2"
          />
          {/* Text Lines */}
          <rect x="170" y="80" width="100" height="8" rx="2" fill="var(--lines-subtle)" />
          <rect x="170" y="100" width="160" height="4" rx="1" fill="var(--surfaces-muted)" />
          <rect x="170" y="110" width="140" height="4" rx="1" fill="var(--surfaces-muted)" />

          <rect x="170" y="140" width="80" height="8" rx="2" fill="var(--lines-subtle)" />
          <rect x="170" y="160" width="160" height="4" rx="1" fill="var(--surfaces-muted)" />
          <rect x="170" y="170" width="150" height="4" rx="1" fill="var(--surfaces-muted)" />
          <rect x="170" y="180" width="130" height="4" rx="1" fill="var(--surfaces-muted)" />

          <rect x="170" y="210" width="90" height="8" rx="2" fill="var(--lines-subtle)" />
          <rect x="170" y="230" width="160" height="4" rx="1" fill="var(--surfaces-muted)" />
          <rect x="170" y="240" width="140" height="4" rx="1" fill="var(--surfaces-muted)" />

          {/* The Path (Animated) */}
          {stage === 1 && (
            <>
              <path
                d="M 120 90 L 160 90 L 160 150 L 160 220 L 180 220"
                stroke="var(--brand-accent)"
                strokeWidth="3"
                strokeDasharray="300"
                strokeDashoffset="300"
                fill="none"
                className="animate-[drawPath_1.5s_ease-out_forwards]"
              />
              <circle
                cx="120"
                cy="90"
                r="4"
                fill="var(--brand-accent)"
                className="animate-[fadeIn_0.3s_ease-out_forwards]"
              />
              <circle
                cx="160"
                cy="150"
                r="4"
                fill="var(--brand-accent)"
                className="animate-[fadeIn_0.3s_ease-out_0.5s_forwards] opacity-0"
              />
              <circle
                cx="180"
                cy="220"
                r="4"
                fill="var(--brand-accent)"
                className="animate-[fadeIn_0.3s_ease-out_1.2s_forwards] opacity-0"
              />

              {/* Floating Label: "Start Here" */}
              <g className="animate-[slideRight_0.5s_ease-out_forwards]">
                <rect x="40" y="75" width="70" height="30" rx="15" fill="var(--brand-accent)" />
                <text
                  x="75"
                  y="95"
                  textAnchor="middle"
                  fill="white"
                  fontSize="12"
                  fontWeight="bold"
                >
                  Start
                </text>
              </g>
            </>
          )}
        </g>

        {/* --- STAGE 2: THE LENS (Dashboard) --- */}
        <g
          className={`transition-all duration-700 ${stage === 2 ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-4'}`}
        >
          {/* Dimmed Document Background */}
          {stage === 2 && (
            <rect
              x="150"
              y="50"
              width="200"
              height="300"
              rx="8"
              fill="var(--surfaces-base)"
              stroke="var(--lines-subtle)"
              strokeWidth="2"
              className="opacity-50"
            />
          )}

          {/* Focus Frame */}
          <g className="animate-[float_3s_ease-in-out_infinite]">
            <rect
              x="160"
              y="130"
              width="180"
              height="80"
              rx="4"
              fill="transparent"
              stroke="var(--brand-accent)"
              strokeWidth="2"
              strokeDasharray="10 5"
            />
            {/* Highlighted Text inside Frame */}
            <rect x="170" y="140" width="80" height="8" rx="2" fill="var(--text-primary)" />
            <rect
              x="170"
              y="160"
              width="160"
              height="4"
              rx="1"
              fill="var(--brand-accent)"
              fillOpacity="0.5"
            />
            <rect
              x="170"
              y="170"
              width="150"
              height="4"
              rx="1"
              fill="var(--brand-accent)"
              fillOpacity="0.5"
            />
          </g>

          {/* Insight Card (Pop-out) */}
          <g className="animate-[popIn_0.5s_cubic-bezier(0.175,0.885,0.32,1.275)_0.3s_forwards] opacity-0 origin-center">
            <line
              x1="340"
              y1="170"
              x2="380"
              y2="170"
              stroke="var(--brand-accent)"
              strokeWidth="2"
            />
            <rect
              x="380"
              y="120"
              width="140"
              height="100"
              rx="8"
              fill="var(--surfaces-raised)"
              stroke="var(--lines-subtle)"
              strokeWidth="1"
              className="shadow-xl"
            />

            {/* Card Content */}
            <text
              x="400"
              y="145"
              fill="var(--brand-accent)"
              fontSize="10"
              fontWeight="bold"
              letterSpacing="1"
            >
              INSIGHT
            </text>
            <text x="400" y="165" fill="var(--text-primary)" fontSize="12" fontWeight="bold">
              Risk Factor
            </text>
            <text x="400" y="185" fill="var(--text-secondary)" fontSize="10">
              &ldquo;Supply chain volatility&rdquo;
            </text>
            <rect x="400" y="200" width="100" height="4" rx="2" fill="var(--surfaces-muted)" />
            <rect x="400" y="200" width="70" height="4" rx="2" fill="var(--action-warning)" />
          </g>
        </g>

        {/* --- STAGE 3: THE KNOWLEDGE (Saved) --- */}
        <g className={`transition-all duration-700 ${stage === 3 ? 'opacity-100' : 'opacity-0'}`}>
          {/* The Stack */}
          <g className="animate-[stackUp_0.8s_ease-out_forwards]">
            <rect
              x="160"
              y="60"
              width="180"
              height="280"
              rx="6"
              fill="var(--surfaces-muted)"
              stroke="var(--lines-subtle)"
              className="opacity-60"
            />
            <rect
              x="155"
              y="55"
              width="190"
              height="290"
              rx="7"
              fill="var(--surfaces-raised)"
              stroke="var(--lines-subtle)"
              className="opacity-80"
            />
            <rect
              x="150"
              y="50"
              width="200"
              height="300"
              rx="8"
              fill="var(--surfaces-base)"
              stroke="var(--lines-subtle)"
              strokeWidth="2"
            />
          </g>

          {/* Saved Badge */}
          <g className="animate-[scaleIn_0.4s_ease-out_0.6s_forwards] opacity-0 origin-center">
            <circle
              cx="250"
              cy="200"
              r="40"
              fill="var(--surfaces-raised)"
              stroke="var(--brand-accent)"
              strokeWidth="2"
              className="shadow-lg"
            />
            <path
              d="M 235 200 L 245 210 L 265 190"
              stroke="var(--brand-accent)"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </g>

          {/* Floating Tags */}
          <g className="animate-[float_4s_ease-in-out_infinite_reverse]">
            <rect
              x="360"
              y="80"
              width="80"
              height="24"
              rx="12"
              fill="var(--brand-accent)"
              fillOpacity="0.1"
              stroke="var(--brand-accent)"
            />
            <text x="400" y="96" textAnchor="middle" fill="var(--brand-accent)" fontSize="10">
              Saved
            </text>
          </g>
          <g className="animate-[float_5s_ease-in-out_1s_infinite]">
            <rect
              x="60"
              y="280"
              width="100"
              height="24"
              rx="12"
              fill="var(--surfaces-raised)"
              stroke="var(--lines-subtle)"
            />
            <text x="110" y="296" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">
              10-K • 2m ago
            </text>
          </g>
        </g>
      </svg>

      <style>{`
        @keyframes drawPath {
          to { stroke-dashoffset: 0; }
        }
        @keyframes fadeIn {
          to { opacity: 1; }
        }
        @keyframes slideRight {
          from { transform: translateX(-20px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes popIn {
          from { transform: scale(0.8); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        @keyframes stackUp {
          from { transform: translateY(20px) scale(0.95); opacity: 0; }
          to { transform: translateY(0) scale(1); opacity: 1; }
        }
        @keyframes scaleIn {
          from { transform: scale(0); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-5px); }
        }
      `}</style>
    </div>
  )
}
