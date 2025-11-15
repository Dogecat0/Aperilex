export const landingCopy = {
  heroEyebrow: 'Instant comprehension route',
  heroHeadline: 'From filings to clarity in one place.',
  heroSubhead: 'See metrics, sentiment, and risk cues before you ever click into a raw filing.',
  primaryCta: 'Continue to dashboard',
  secondaryCta: 'Review saved analyses',
  featureDeck: {
    eyebrow: 'Feature deck',
    title: 'Every core workflow on one surface',
    description:
      'Filing dashboard, launchpad templates, walkthroughs, filing detail explorer, and saved analyses are represented exactly as they appear in product.',
  },
  journey: {
    eyebrow: 'Deterministic onboarding',
    title: 'Set a goal, launch a template, learn, then save',
    description:
      'The Aperilex path is fixed: declare intent, launch a vetted template, learn through guided walkthroughs, drill into detail, and save trusted artifacts for the next review.',
  },
  socialProof: {
    eyebrow: 'Proof in practice',
    title: 'Saved analyses keep teams aligned',
    description:
      'Usage research and pilot deployments show that teams return to saved workspaces three times per week to refresh walkthrough outcomes and detail highlights.',
    statsLabel: 'Confidence signals that back the journey',
  },
  savedLoop: {
    eyebrow: 'Persistence and recall',
    title: 'Resume the exact analysis you trusted yesterday',
    description:
      'Pinned filings, custom labels, and tracked review times make the save-and-return loop reliable for both exploratory learners and expert reviewers.',
  },
  ctaBanner: {
    title: 'Ready to turn filings into confident briefs?',
    description:
      'Stay inside Aperilex from first glance to saved insight. The dashboard, launchpad, walkthrough, detail explorer, and saved workspace are ready.',
    action: 'Launch Aperilex',
  },
} as const

export type LandingCopy = typeof landingCopy
