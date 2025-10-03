import type { CSSProperties, ReactNode } from 'react'

export type SectionIntroHeadingLevel = 'h1' | 'h2' | 'h3' | 'h4'

export interface SectionIntroProps {
  title: string
  description?: string
  eyebrow?: string
  actions?: ReactNode
  className?: string
  descriptionClassName?: string
  actionsClassName?: string
  as?: SectionIntroHeadingLevel
  titleClassName?: string
  titleStyle?: CSSProperties
}

export function SectionIntro({
  title,
  description,
  eyebrow,
  actions,
  className = '',
  descriptionClassName = '',
  actionsClassName = '',
  as = 'h2',
  titleClassName = '',
  titleStyle,
}: SectionIntroProps) {
  const HeadingTag = as

  return (
    <header
      className={[
        'flex flex-col gap-3 md:flex-row md:items-start md:justify-between',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="flex flex-col gap-2">
        {eyebrow ? (
          <p
            className="text-xs font-semibold uppercase tracking-[0.2em]"
            style={{ color: 'var(--text-secondary)' }}
          >
            {eyebrow}
          </p>
        ) : null}
        <HeadingTag
          className={['text-lg font-semibold text-[var(--text-primary)]', titleClassName]
            .filter(Boolean)
            .join(' ')}
          style={titleStyle}
        >
          {title}
        </HeadingTag>
        {description ? (
          <p
            className={['text-sm leading-relaxed text-[var(--text-muted)]', descriptionClassName]
              .filter(Boolean)
              .join(' ')}
          >
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div
          className={[
            'mt-2 flex shrink-0 flex-col items-start gap-2 md:mt-0 md:items-end',
            actionsClassName,
          ]
            .filter(Boolean)
            .join(' ')}
        >
          {actions}
        </div>
      ) : null}
    </header>
  )
}
