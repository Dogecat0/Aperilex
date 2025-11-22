export const learningProgressResponses = [
  {
    schema_version: 1,
    progress_id: 'progress-mda',
    user_id: 'user-123',
    module_key: 'mda_foundations',
    progress_percent: 60,
    last_interaction_at: '2025-01-05T10:00:00Z',
    completed_at: null,
    is_unlocked: false,
    unlocked_at: null,
    metadata: {
      section_progress_version: 1,
      last_walkthrough_event_at: '2025-01-05T10:00:00Z',
      last_walkthrough_analysis_id: '11111111-1111-1111-1111-111111111111',
      sections: {
        'Item 7 - Management Discussion & Analysis': {
          analysis_runs: {
            '11111111-1111-1111-1111-111111111111': {
              progress_percent: 60,
              last_event_at: '2025-01-05T10:00:00Z',
            },
            '00000000-0000-0000-0000-000000000000': {
              progress_percent: 100,
              last_event_at: '2024-12-15T09:00:00Z',
              completed_at: '2024-12-15T09:05:00Z',
            },
          },
          latest_analysis_id: '11111111-1111-1111-1111-111111111111',
          latest_progress_percent: 60,
          last_event_at: '2025-01-05T10:00:00Z',
          progress_percent: 60,
          completed_analysis_ids: ['00000000-0000-0000-0000-000000000000'],
        },
      },
      analysis_walkthroughs: {
        '11111111-1111-1111-1111-111111111111': {
          progress_percent: 60,
          last_event_at: '2025-01-05T10:00:00Z',
          completed_sections: [],
        },
        '00000000-0000-0000-0000-000000000000': {
          progress_percent: 100,
          last_event_at: '2024-12-15T09:00:00Z',
          completed_sections: ['Item 7 - Management Discussion & Analysis'],
        },
      },
    },
    created_at: '2025-01-05T09:00:00Z',
    updated_at: '2025-01-05T10:00:00Z',
  },
  {
    schema_version: 1,
    progress_id: 'progress-risk',
    user_id: 'user-123',
    module_key: 'risk_mastery',
    progress_percent: 20,
    last_interaction_at: '2025-01-03T14:30:00Z',
    completed_at: null,
    is_unlocked: false,
    unlocked_at: null,
    metadata: {
      section_progress_version: 1,
      last_walkthrough_event_at: '2025-01-03T14:30:00Z',
      last_walkthrough_analysis_id: '11111111-1111-1111-1111-111111111111',
      sections: {
        'Item 1A - Risk Factors': {
          analysis_runs: {
            '11111111-1111-1111-1111-111111111111': {
              progress_percent: 20,
              last_event_at: '2025-01-03T14:30:00Z',
            },
            '22222222-2222-2222-2222-222222222222': {
              progress_percent: 100,
              last_event_at: '2024-12-30T13:10:00Z',
              completed_at: '2024-12-30T13:15:00Z',
            },
          },
          latest_analysis_id: '11111111-1111-1111-1111-111111111111',
          latest_progress_percent: 20,
          last_event_at: '2025-01-03T14:30:00Z',
          progress_percent: 20,
          completed_analysis_ids: ['22222222-2222-2222-2222-222222222222'],
        },
      },
      analysis_walkthroughs: {
        '11111111-1111-1111-1111-111111111111': {
          progress_percent: 20,
          last_event_at: '2025-01-03T14:30:00Z',
          completed_sections: [],
        },
        '22222222-2222-2222-2222-222222222222': {
          progress_percent: 100,
          last_event_at: '2024-12-30T13:10:00Z',
          completed_sections: ['Item 1A - Risk Factors'],
        },
      },
    },
    created_at: '2025-01-03T14:00:00Z',
    updated_at: '2025-01-03T14:30:00Z',
  },
] as const

export const quizAttemptResponses = [
  {
    schema_version: 1,
    attempt_id: 'attempt-1',
    user_id: 'user-123',
    quiz_id: 'mda_foundations',
    question_count: 3,
    correct_count: 2,
    score_percent: 66.7,
    passed: false,
    is_human_reviewed: false,
    attempted_at: '2025-01-04T16:45:00Z',
    metadata: {
      duration_seconds: 48,
      analysis_id: '11111111-1111-1111-1111-111111111111',
      module_key: 'mda_foundations',
    },
    created_at: '2025-01-04T16:45:00Z',
    updated_at: '2025-01-04T16:45:00Z',
  },
  {
    schema_version: 1,
    attempt_id: 'attempt-2',
    user_id: 'user-123',
    quiz_id: 'risk_mastery',
    question_count: 3,
    correct_count: 3,
    score_percent: 100,
    passed: true,
    is_human_reviewed: false,
    attempted_at: '2025-01-02T11:15:00Z',
    metadata: {
      duration_seconds: 35,
      analysis_id: '11111111-1111-1111-1111-111111111111',
      module_key: 'risk_mastery',
    },
    created_at: '2025-01-02T11:15:00Z',
    updated_at: '2025-01-02T11:15:00Z',
  },
] as const
