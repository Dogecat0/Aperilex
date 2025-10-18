export const landingCopy = {
  heroEyebrow: 'Research-ready in minutes',
  heroHeadline: 'Aperilex turns SEC filings into confident investing stories',
  heroSubhead:
    'Grounded in our usage research, Aperilex serves curious learners with guidance, context, and clear next steps.',
  primaryCta: 'Launch Aperilex',
  secondaryCta: 'See how it works',
  personas: [
    {
      id: 'guided',
      label: 'Guided explorers',
      badge: 'Conversational guidance',
      title: 'Guided explorers',
      description:
        'Newer investors who lean on conversational tools for clarity. Aperilex walks them through filings with plain-language primers, learning cues, and suggested questions.',
      support: 'Built around structured onboarding and contextual learning tracks.',
    },
    {
      id: 'focused',
      label: 'Focused analysts',
      badge: 'Instant verification',
      title: 'Focused analysts',
      description:
        'Experienced readers who want fast verification. Aperilex spotlights deltas, sentiment, and emerging signals so they can validate assumptions in seconds.',
      support: 'Pairs cached insights with frictionless drill-down controls.',
    },
  ],
  highlights: [
    {
      title: 'Explain more, instantly',
      description:
        'Launch LLM follow-ups that stay tethered to trusted summaries, quotes, and metrics so you never lose the audit trail.',
    },
    {
      title: 'Learn by doing',
      description:
        'Micro-lessons, primers, and checklists appear right beside the analysis so confidence grows with every filing.',
    },
    {
      title: 'Signals without noise',
      description:
        'Tiered queues and schema-versioned insights keep comparisons current across quarters, peers, and risk surfaces.',
    },
  ],
  researchCallout: {
    title: 'Designed from real usage patterns',
    description:
      "Our economic research on ChatGPT adoption shows two dominant behaviors: quick validation and exploratory learning. Aperilex unites both so teams don't have to juggle tools.",
    bullets: [
      'Adaptive guidance keeps first-time readers oriented without overwhelming detail.',
      'Snapshot dashboards respect expert workflows with ready-to-export insights.',
      'Every interaction reinforces trusted sources—filing context stays one tap away.',
    ],
  },
  walkthrough: {
    title: 'What the first session feels like',
    steps: [
      {
        title: 'Set your goal',
        description:
          'Tell Aperilex whether you are validating a thesis or learning the structure of a new filing.',
      },
      {
        title: 'Review instant insights',
        description:
          'See deltas, sentiment, and key risks—with confidence bands and sourced excerpts.',
      },
      {
        title: 'Drill deeper with guidance',
        description:
          'Open contextual primers, suggested follow-up questions, and learning checklists tuned to your chosen outcome.',
      },
    ],
  },
  ctaBanner: {
    title: 'Ready to reimagine filing analysis?',
    description:
      'Join teams who learn faster and decide with conviction—start exploring Aperilex today.',
    action: 'Get started',
  },
} as const

export type LandingCopy = typeof landingCopy
