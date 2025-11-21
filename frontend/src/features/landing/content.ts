export type HeroInsight = {
  title: string
  description: string
}

type HeroSlidePanel =
  | {
      type: 'launchpad'
      heading: string
      fields: {
        label: string
        helper: string
      }[]
      templates: {
        name: string
        helper: string
      }[]
    }
  | {
      type: 'dashboard'
      heading: string
      stats: {
        label: string
        description: string
      }[]
      filters: {
        label: string
        value: string
      }[]
    }
  | {
      type: 'saved'
      heading: string
      entries: {
        company: string
        label: string
        reviewedAt: string
      }[]
      helper: string
    }

export type HeroSlide = {
  id: string
  label: string
  description: string
  panel: HeroSlidePanel
}

export type FeatureTileCta = {
  label: string
  path: string
}

export const heroInsights: HeroInsight[] = [
  {
    title: 'Launchpad search + templates',
    description:
      'The Analyze Filings workspace requires a ticker, optional form filters, and a template pick before any workflow starts.',
  },
  {
    title: 'Dashboard filters and rollups',
    description:
      'Filing dashboard stats and filters use the same filing type, date range, and segment controls that gate the rest of the product.',
  },
  {
    title: 'Saved analysis handoff',
    description:
      'Saved workspace cards validate each analysis before opening and keep the saved-at timestamp in view.',
  },
]

export type DashboardTileContent = {
  title: string
  description: string
  summaryCards: {
    label: string
    value: string
    helper: string
  }[]
  filters: {
    label: string
    value: string
  }[]
  navigationHint: string
  cta: FeatureTileCta
}

export type LaunchpadTileContent = {
  title: string
  description: string
  templates: {
    id: string
    name: string
    description: string
    meta: {
      label: string
      value: string
    }
    outputs: string[]
  }[]
  navigationHint: string
  cta: FeatureTileCta
}

export type LearningTileContent = {
  title: string
  description: string
  walkthroughName: string
  steps: {
    id: number
    title: string
    description: string
  }[]
  toggles: {
    label: string
    enabled: boolean
  }[]
  navigationHint: string
  cta: FeatureTileCta
}

export type DetailTileContent = {
  title: string
  description: string
  tabs: string[]
  metrics: {
    label: string
    value: string
    tone: 'positive' | 'neutral' | 'caution'
  }[]
  navigationHint: string
  cta: FeatureTileCta
}

export type SavedTileContent = {
  title: string
  description: string
  entries: {
    company: string
    label: string
    reviewedAt: string
  }[]
  tags: string[]
  navigationHint: string
  cta: FeatureTileCta
}

export type FeatureDeckContent = {
  dashboard: DashboardTileContent
  launchpad: LaunchpadTileContent
  learning: LearningTileContent
  detail: DetailTileContent
  saved: SavedTileContent
}

export const featureDeckContent: FeatureDeckContent = {
  dashboard: {
    title: 'Filing Dashboard',
    description:
      'Hero stats mirror completed runs, guided coverage, and your latest finished filing, and the filter preview shows the same chips that gate filing type, date range, and template focus in app.',
    summaryCards: [
      { label: 'Completed analyses', value: '42', helper: 'Past last month' },
      { label: 'Guided sections ready', value: '118', helper: 'Walkthrough coverage' },
      { label: 'Latest completion', value: 'Aurora Labs', helper: '10-K • Mar 8' },
    ],
    filters: [
      { label: 'Filing type', value: '10-K Comprehensive' },
      { label: 'Date range', value: 'Last month' },
      { label: 'Analysis template', value: 'Comprehensive' },
    ],
    navigationHint: 'Nav → Filing Dashboard',
    cta: { label: 'Open dashboard', path: '/dashboard' },
  } satisfies DashboardTileContent,
  launchpad: {
    title: 'Analysis Launchpad',
    description:
      'Ticker search, SEC form filters, duplicate detection, and the template rail all match the Analyze Filings workspace so visitors see the exact levers used to queue real analyses.',
    templates: [
      {
        id: 'comprehensive',
        name: 'Comprehensive',
        description: 'Primary queue that produces guided walkthroughs plus metrics and sentiment.',
        meta: {
          label: 'Command',
          value: 'Full analysis run',
        },
        outputs: ['Guided sections', 'Headline metrics', 'Sentiment brief'],
      },
      {
        id: 'financial',
        name: 'Financial',
        description: 'Triggers the KPI extract practice command for statement-heavy scans.',
        meta: {
          label: 'Practice',
          value: 'KPI extract',
        },
        outputs: ['KPI board', 'Variance digest'],
      },
      {
        id: 'risk',
        name: 'Risk',
        description: 'Queues the risk delta practice command to surface flagged sections.',
        meta: {
          label: 'Practice',
          value: 'Risk delta',
        },
        outputs: ['Risk synopsis', 'Confidence band'],
      },
      {
        id: 'business_focused',
        name: 'MD&A focus',
        description: 'MD&A quiz practice command that returns comprehension prompts and cues.',
        meta: {
          label: 'Practice',
          value: 'MD&A quiz',
        },
        outputs: ['Quiz prompts', 'Walkthrough checkpoints'],
      },
    ],
    navigationHint: 'Nav → Analysis Launchpad',
    cta: { label: 'Choose template', path: '/analyze' },
  } satisfies LaunchpadTileContent,
  learning: {
    title: 'Learning Hub Walkthroughs',
    description:
      'Learning Hub cards reuse the exact guided sections, comprehension checks, and lesson links you resume inside the product.',
    walkthroughName: 'MD&A guided review workflow',
    steps: [
      {
        id: 1,
        title: 'Resume guided module',
        description:
          'Landing CTA routes into the same walkthrough state tracked on Learning Hub cards.',
      },
      {
        id: 2,
        title: 'Study highlights',
        description:
          'Guided section panels surface focus copy plus filing-specific highlight callouts.',
      },
      {
        id: 3,
        title: 'Answer comprehension checks',
        description: 'Multiple-choice checks validate takeaways before progress advances.',
      },
      {
        id: 4,
        title: 'Log progress + reopen detail view',
        description:
          'Finishing a section updates Learning Hub progress and deep-links back to `/filing/:id`.',
      },
    ],
    toggles: [
      { label: 'Guided sections', enabled: true },
      { label: 'Comprehension checks', enabled: true },
      { label: 'Lesson links', enabled: true },
    ],
    navigationHint: 'Nav → Learning Hub',
    cta: { label: 'Open walkthroughs', path: '/learn' },
  } satisfies LearningTileContent,
  detail: {
    title: 'Filing Detail Explorer',
    description:
      'Tabbed layout mirrors the Overview, Guided walkthrough, Metrics, Sentiment, and Structured output tabs that open from each dashboard analysis.',
    tabs: ['Overview', 'Guided walkthrough', 'Metrics', 'Sentiment', 'Structured output'],
    metrics: [
      {
        label: 'YoY delta',
        value: '+4.6%',
        tone: 'positive',
      },
      {
        label: 'Sentiment',
        value: 'Stabilized',
        tone: 'neutral',
      },
      {
        label: 'Excerpt',
        value: '“Margin lift driven by automation investments.”',
        tone: 'neutral',
      },
    ],
    navigationHint: 'Dashboard → Open filing detail',
    cta: { label: 'View analyses', path: '/dashboard' },
  } satisfies DetailTileContent,
  saved: {
    title: 'Saved Analyses Workspace',
    description:
      'Saved entries store ticker info, filing type, and timestamps, then validate availability before reopening the exact analysis.',
    entries: [
      {
        company: 'Aurora Labs',
        label: '10-K • Comprehensive template',
        reviewedAt: 'Saved 12h ago',
      },
      {
        company: 'Northwind Renewables',
        label: '10-Q • Financial template',
        reviewedAt: 'Saved 2d ago',
      },
      { company: 'Helix Bio', label: 'MD&A focus', reviewedAt: 'Saved 5d ago' },
    ],
    tags: ['Availability check', 'Timestamped', 'One-tap resume'],
    navigationHint: 'Nav → Saved Items',
    cta: { label: 'Resume saved analysis', path: '/saved' },
  } satisfies SavedTileContent,
}

export const heroSlides: HeroSlide[] = [
  {
    id: 'launchpad-intake',
    label: 'Launchpad intake',
    description:
      'Analyze Filings asks for a ticker, optional form filters, and a template pick before the run begins.',
    panel: {
      type: 'launchpad',
      heading: 'Analysis Launchpad',
      fields: [
        { label: 'Ticker', helper: 'Required to fetch filings (e.g., AAPL)' },
        { label: 'Form type', helper: 'Optional filter (10-K, 10-Q)' },
        { label: 'Date range', helper: 'Default recent filings, adjustable window' },
        { label: 'Sort order', helper: 'Newest filings first' },
      ],
      templates: [
        { name: 'Comprehensive', helper: 'Full walkthrough across sections' },
        { name: 'Financial focus', helper: 'KPI extract across statements' },
        { name: 'Risk focus', helper: 'Risk factor delta plus cues' },
        { name: 'MD&A focus', helper: 'Narrative and practice prompts' },
      ],
    },
  },
  {
    id: 'dashboard-rollup',
    label: 'Dashboard rollup',
    description:
      'Filing dashboard stats track completions, guided sections, and latest filings per selected filters.',
    panel: {
      type: 'dashboard',
      heading: 'Dashboard overview',
      stats: [
        {
          label: 'Completed analyses',
          description: 'Counts update once an analysis finishes for the selected range.',
        },
        {
          label: 'Guided sections covered',
          description: 'Reflects how many walkthrough sections are complete.',
        },
        {
          label: 'Latest completion',
          description: 'Shows the most recent filing type and completion date.',
        },
      ],
      filters: [
        { label: 'Filing type', value: 'All filings' },
        { label: 'Date range', value: 'Past 30 days' },
        { label: 'Segment focus', value: 'All segments' },
      ],
    },
  },
  {
    id: 'saved-drawer',
    label: 'Saved workspace handoff',
    description:
      'Saved workspace reopens analyses in-place after verifying they still exist on the backend.',
    panel: {
      type: 'saved',
      heading: 'Saved analyses',
      entries: [
        { company: 'Aurora Labs', label: '10-K filing', reviewedAt: 'Saved 12h ago' },
        { company: 'Northwind Renewables', label: '10-Q filing', reviewedAt: 'Saved 2d ago' },
        { company: 'Helix Bio', label: 'MD&A walkthrough', reviewedAt: 'Saved 5d ago' },
      ],
      helper: 'Each entry checks availability before routing you into the filing detail view.',
    },
  },
]

export type JourneyStep = {
  id: string
  title: string
  description: string
  snippet: {
    label: string
    pills: string[]
  }
}

export const journeyRail: JourneyStep[] = [
  {
    id: 'goal',
    title: 'Set your goal',
    description:
      'Choose whether you are validating a thesis, exploring a sector, or learning a filing structure.',
    snippet: {
      label: 'Goal chips',
      pills: ['Validate thesis', 'Explore sector', 'Learn structure'],
    },
  },
  {
    id: 'launch',
    title: 'Launch template',
    description:
      'Pick the template with the right balance of deltas, walkthroughs, or risk coverage.',
    snippet: {
      label: 'Template panel',
      pills: ['Comprehensive', 'Financial', 'Risk'],
    },
  },
  {
    id: 'learn',
    title: 'Learn & drill down',
    description: 'Follow walkthrough steps while drilling into the detail explorer tabs.',
    snippet: {
      label: 'Guided steps',
      pills: ['Primer', 'Quiz', 'Callouts'],
    },
  },
  {
    id: 'save',
    title: 'Save & revisit',
    description: 'Pin the analysis so the same context is waiting when you return.',
    snippet: {
      label: 'Saved workspace',
      pills: ['Pinned filings', 'Custom labels', 'Review timestamps'],
    },
  },
]

export type SocialProofContent = {
  stats: {
    label: string
    value: string
    context: string
  }[]
  testimonials: {
    quote: string
    author: string
    role: string
    feature: string
  }[]
  savedShowcase: {
    heading: string
    description: string
    highlights: string[]
  }
}

export const socialProofContent: SocialProofContent = {
  stats: [
    {
      label: 'Saved workspace reuse',
      value: '3x / week',
      context: 'Average return cadence per pilot team',
    },
    {
      label: 'Launchpad adoption',
      value: '87%',
      context: 'Teams starting every filing from templates',
    },
    {
      label: 'Walkthrough completion',
      value: '92%',
      context: 'Learners finishing MD&A guidance path',
    },
  ],
  testimonials: [
    {
      quote:
        '“The dashboard preview tells our analysts exactly which deltas will matter before they start reading.”',
      author: 'Research lead, Aurora Growth',
      role: 'Filing dashboard pilot',
      feature: 'Filing dashboard',
    },
    {
      quote:
        '“Saved analyses replaced our note docs. The labels and timestamps keep everyone aligned.”',
      author: 'Director of Research Ops, Northwind',
      role: 'Saved workspace rollout',
      feature: 'Saved analyses',
    },
  ],
  savedShowcase: {
    heading: 'Saved workspace confidence loop',
    description:
      'Pinned filings hold the precise deltas, walkthrough checkpoints, and callouts that got your team to conviction. Returning to a saved card means you never lose that thread.',
    highlights: [
      'Labels clarify the intent of each saved analysis.',
      'Review timestamps surface freshness at a glance.',
      'Pinned excerpts remind you where insights originated.',
    ],
  },
}
