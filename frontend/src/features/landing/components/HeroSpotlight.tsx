import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/Button'
import type { HeroInsight, HeroSlide } from '../content'
import { renderPanelContent } from './renderPanelContent'

type HeroSpotlightProps = {
  eyebrow: string
  headline: string
  subhead: string
  primaryLabel: string
  secondaryLabel: string
  insights: HeroInsight[]
  slides: HeroSlide[]
  isAuthenticating: boolean
  onPrimaryCta: () => void
  onSecondaryCta: () => void
}

export function HeroSpotlight({
  eyebrow,
  headline,
  subhead,
  primaryLabel,
  secondaryLabel,
  insights,
  slides,
  isAuthenticating,
  onPrimaryCta,
  onSecondaryCta,
}: HeroSpotlightProps) {
  const slideOptions = useMemo(() => slides, [slides])
  const [activeSlideId, setActiveSlideId] = useState(slideOptions[0]?.id ?? '')
  const activeSlide = useMemo(
    () => slideOptions.find((slide) => slide.id === activeSlideId) ?? slideOptions[0],
    [activeSlideId, slideOptions]
  )
  const panelRef = useRef<HTMLDivElement | null>(null)
  const measurementRef = useRef<HTMLDivElement | null>(null)
  const [panelHeight, setPanelHeight] = useState(0)

  useLayoutEffect(() => {
    const measurementNode = measurementRef.current
    if (measurementNode) {
      const heights = Array.from(measurementNode.children)
        .map((child) => (child instanceof HTMLElement ? child.offsetHeight : 0))
        .filter((value) => value > 0)
      const maxHeight = heights.length ? Math.max(...heights) : 0
      if (maxHeight > 0) {
        setPanelHeight((prev) =>
          prev === 0 ? Math.ceil(maxHeight) : Math.max(prev, Math.ceil(maxHeight))
        )
      }
    }

    if (typeof window === 'undefined' || typeof ResizeObserver === 'undefined') {
      return
    }

    const node = panelRef.current
    if (!node) {
      return
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) {
        return
      }

      const measured = Math.ceil(entry.contentRect.height)
      setPanelHeight((prev) => {
        if (measured === 0) {
          return prev
        }
        return prev === 0 ? measured : Math.max(prev, measured)
      })
    })

    observer.observe(node)
    return () => observer.disconnect()
  }, [slideOptions])
  const renderSlidePanel = () => {
    if (!activeSlide) {
      return null
    }
    return renderPanelContent(activeSlide.panel)
  }

  return (
    <section
      aria-labelledby="landing-hero-heading"
      className="relative overflow-hidden text-[var(--text-on-brand)]"
      style={{
        background:
          'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.15), transparent), var(--brand-background)',
      }}
    >
      <div className="absolute inset-0 opacity-50 mix-blend-screen" aria-hidden>
        <div className="absolute -left-32 -top-10 h-96 w-96 rounded-full bg-[var(--learning-surface)] blur-3xl" />
      </div>

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-12 px-6 py-24 lg:flex-row lg:items-center lg:gap-16">
        <div
          ref={measurementRef}
          className="pointer-events-none absolute left-0 top-0 -z-10 max-w-xl opacity-0"
          aria-hidden
        >
          {slideOptions.map((slide) => (
            <div
              key={`${slide.id}-measurement`}
              className="rounded-[32px] border border-white/15 bg-white/5 p-6"
            >
              <div className="rounded-3xl border border-white/15 bg-[var(--brand-background)] p-4">
                {renderPanelContent(slide.panel)}
              </div>
              <p className="pt-4 text-sm text-white/80">{slide.description}</p>
            </div>
          ))}
        </div>
        <div className="flex-1 space-y-6">
          <p
            className="text-xs font-semibold uppercase tracking-[0.35em]"
            style={{ color: 'rgba(255,255,255,0.72)' }}
          >
            {eyebrow}
          </p>
          <h1 id="landing-hero-heading" className="text-4xl font-semibold leading-tight">
            {headline}
          </h1>
          <p className="text-base" style={{ color: 'rgba(245,247,255,0.85)' }}>
            {subhead}
          </p>

          <div className="flex flex-col gap-4 pt-2 sm:flex-row">
            <Button
              type="button"
              onClick={onPrimaryCta}
              disabled={isAuthenticating}
              className="w-full sm:w-auto"
            >
              {isAuthenticating ? 'Preparing workspace…' : primaryLabel}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={onSecondaryCta}
              className="w-full sm:w-auto"
              style={{
                background: 'transparent',
                color: 'var(--text-on-brand)',
                borderColor: 'rgba(255,255,255,0.25)',
              }}
            >
              {secondaryLabel}
            </Button>
          </div>

          <div className="grid gap-4 pt-6 sm:grid-cols-3">
            {insights.map((insight) => (
              <article
                key={insight.title}
                className="rounded-2xl border border-white/15 bg-white/5 p-4 backdrop-blur"
              >
                <h3 className="text-sm font-semibold text-white">{insight.title}</h3>
                <p className="pt-2 text-sm text-[var(text-on-muted)]">{insight.description}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="flex-1 space-y-4">
          <div className="inline-flex rounded-full border border-white/20 bg-white/5 p-1 text-xs font-semibold text-white/70">
            {slideOptions.map((slide) => {
              const isActive = slide.id === activeSlide?.id
              return (
                <button
                  key={slide.id}
                  type="button"
                  onClick={() => setActiveSlideId(slide.id)}
                  className={`rounded-full px-3 py-1 transition ${
                    isActive
                      ? 'bg-white text-[var(--brand-surface)]'
                      : 'text-white/70 hover:text-white'
                  }`}
                >
                  {slide.label}
                </button>
              )
            })}
          </div>

          <div
            ref={panelRef}
            className="relative rounded-[32px] border border-white/15 bg-white/5 p-6 shadow-[var(--shadows-medium)] backdrop-blur"
            aria-live="polite"
            style={{ minHeight: panelHeight ? `${panelHeight}px` : undefined }}
          >
            {activeSlide && (
              <>
                <div className="rounded-3xl border border-white/15 bg-[var(--brand-surface)] p-4">
                  {renderSlidePanel()}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
