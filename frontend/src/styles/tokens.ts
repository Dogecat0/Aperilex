export interface ThemeTokens {
  name: 'light' | 'dark'
  brand: {
    background: string
    surface: string
    accent: string
  }
  learning: {
    surface: string
    accent: string
  }
  action: {
    primary: string
    primaryContrast: string
    secondary: string
  }
  surfaces: {
    base: string
    raised: string
    muted: string
    overlay: string
  }
  text: {
    primary: string
    secondary: string
    muted: string
    onBrand: string
    onLearning: string
    onMuted: string
  }
  lines: {
    subtle: string
    strong: string
    focus: string
  }
  status: {
    positive: string
    neutral: string
    negative: string
    warning: string
  }
  metrics: {
    up: string
    down: string
    stable: string
  }
  data: {
    neutral: string
    emphasis: string
    chartSeries: string[]
  }
  focus: {
    ring: string
    shadow: string
  }
  spacing: {
    xxs: string
    xs: string
    sm: string
    md: string
    lg: string
    xl: string
    xxl: string
    xxxl: string
  }
  typography: {
    sans: string
    serif: string
    mono: string
    weights: {
      heading: number
      subheading: number
      body: number
      caption: number
      numeric: number
    }
    lineHeights: {
      dense: number
      standard: number
      relaxed: number
    }
    letterSpacing: {
      tight: string
      normal: string
    }
  }
  shadows: {
    soft: string
    medium: string
    strong: string
  }
}

export const lightTokens: ThemeTokens = {
  name: 'light',
  brand: {
    background: '#091831',
    surface: '#132540',
    accent: '#8F86E4',
  },
  learning: {
    surface: '#FFF4DE',
    accent: '#d99751ff',
  },
  action: {
    primary: '#45C388',
    primaryContrast: '#04121F',
    secondary: '#9BE5C2',
  },
  surfaces: {
    base: '#F5F7FF',
    raised: '#FFFFFF',
    muted: '#E7EAF6',
    overlay: 'rgba(231, 234, 246, 0.92)',
  },
  text: {
    primary: '#0B1628',
    secondary: '#2F374A',
    muted: '#737C91',
    onBrand: '#F5F7FF',
    onLearning: '#1A0E00',
    onMuted: '#091831',
  },
  lines: {
    subtle: '#D8DCE5',
    strong: '#9DA8C8',
    focus: '#45C388',
  },
  status: {
    positive: '#45C388',
    neutral: '#B9B2F2',
    negative: '#E75C4A',
    warning: '#E78C1F',
  },
  metrics: {
    up: '#138352',
    down: '#E75C4A',
    stable: '#737C91',
  },
  data: {
    neutral: '#ABB2C3',
    emphasis: '#8F86E4',
    chartSeries: ['#091831', '#45C388', '#F5B15C', '#8F86E4', '#E75C4A', '#13A38C'],
  },
  focus: {
    ring: '#45C388',
    shadow: '0 0 0 4px rgba(69, 195, 136, 0.18)',
  },
  spacing: {
    xxs: '0.125rem',
    xs: '0.25rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    xxl: '2rem',
    xxxl: '3rem',
  },
  typography: {
    sans: '"Inter Variable", "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    serif: '"Newsreader", "Georgia", serif',
    mono: '"Roboto Mono", "Fira Code", monospace',
    weights: {
      heading: 700,
      subheading: 550,
      body: 425,
      caption: 375,
      numeric: 600,
    },
    lineHeights: {
      dense: 1.2,
      standard: 1.45,
      relaxed: 1.6,
    },
    letterSpacing: {
      tight: '-0.01em',
      normal: '0em',
    },
  },
  shadows: {
    soft: '0 3px 8px rgba(9, 24, 49, 0.12)',
    medium: '0 8px 20px rgba(9, 24, 49, 0.14)',
    strong: '0 12px 28px rgba(9, 24, 49, 0.18)',
  },
}

export const darkTokens: ThemeTokens = {
  name: 'dark',
  brand: {
    background: '#020b1a',
    surface: '#0B1628',
    accent: '#4F5EC5',
  },
  learning: {
    surface: '#2C1F12',
    accent: '#dca558ff',
  },
  action: {
    primary: '#3ED79E',
    primaryContrast: '#04161F',
    secondary: '#1F8E65',
  },
  surfaces: {
    base: '#030918',
    raised: '#061021ff',
    muted: '#102136',
    overlay: 'rgba(3, 9, 24, 0.88)',
  },
  text: {
    primary: '#F5F7FF',
    secondary: '#AAB7DD',
    muted: '#7A87A8',
    onBrand: '#E0F7EC',
    onLearning: '#FFE8C2',
    onMuted: '#E7EAF6',
  },
  lines: {
    subtle: 'rgba(154, 168, 200, 0.35)',
    strong: 'rgba(231, 234, 246, 0.55)',
    focus: '#3ED79E',
  },
  status: {
    positive: '#3ED79E',
    neutral: '#AFA5FF',
    negative: '#FB7185',
    warning: '#C9733A',
  },
  metrics: {
    up: '#3ED79E',
    down: '#FB7185',
    stable: '#AAB7DD',
  },
  data: {
    neutral: '#3A4459',
    emphasis: '#AFA5FF',
    chartSeries: ['#7AA2FF', '#3ED79E', '#FFA04D', '#AFA5FF', '#FB7185', '#13A38C'],
  },
  focus: {
    ring: '#3ED79E',
    shadow: '0 0 0 4px rgba(62, 215, 158, 0.24)',
  },
  spacing: {
    xxs: '0.125rem',
    xs: '0.25rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    xxl: '2rem',
    xxxl: '3rem',
  },
  typography: {
    sans: '"Inter Variable", "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    serif: '"Newsreader", "Georgia", serif',
    mono: '"Roboto Mono", "Fira Code", monospace',
    weights: {
      heading: 700,
      subheading: 550,
      body: 425,
      caption: 375,
      numeric: 600,
    },
    lineHeights: {
      dense: 1.2,
      standard: 1.45,
      relaxed: 1.6,
    },
    letterSpacing: {
      tight: '-0.01em',
      normal: '0em',
    },
  },
  shadows: {
    soft: '0 4px 14px rgba(3, 9, 24, 0.35)',
    medium: '0 8px 22px rgba(0, 0, 0, 0.45)',
    strong: '0 12px 30px rgba(0, 0, 0, 0.55)',
  },
}
