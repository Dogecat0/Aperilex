export const learningProgressResponses = [
  {
    schema_version: 1,
    progress_id: 'progress-mda',
    user_id: 'user-123',
    module_key: 'mda_foundations',
    progress_percent: 60,
    last_interaction_at: '2025-01-05T10:00:00Z',
    completed_at: null,
    pending_review_count: 2,
    last_reviewed_at: null,
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
          },
          latest_analysis_id: '11111111-1111-1111-1111-111111111111',
          latest_progress_percent: 60,
          last_event_at: '2025-01-05T10:00:00Z',
          progress_percent: 60,
          completed_analysis_ids: [],
        },
      },
      analysis_walkthroughs: {
        '11111111-1111-1111-1111-111111111111': {
          progress_percent: 60,
          last_event_at: '2025-01-05T10:00:00Z',
          completed_sections: [],
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
    pending_review_count: 1,
    last_reviewed_at: null,
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
          },
          latest_analysis_id: '11111111-1111-1111-1111-111111111111',
          latest_progress_percent: 20,
          last_event_at: '2025-01-03T14:30:00Z',
          progress_percent: 20,
          completed_analysis_ids: [],
        },
      },
      analysis_walkthroughs: {
        '11111111-1111-1111-1111-111111111111': {
          progress_percent: 20,
          last_event_at: '2025-01-03T14:30:00Z',
          completed_sections: [],
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
    quiz_id: 'practice-check',
    question_count: 3,
    correct_count: 2,
    score_percent: 66.7,
    passed: false,
    is_human_reviewed: false,
    attempted_at: '2025-01-04T16:45:00Z',
    metadata: { duration_seconds: 48 },
    created_at: '2025-01-04T16:45:00Z',
    updated_at: '2025-01-04T16:45:00Z',
  },
  {
    schema_version: 1,
    attempt_id: 'attempt-2',
    user_id: 'user-123',
    quiz_id: 'practice-check',
    question_count: 3,
    correct_count: 3,
    score_percent: 100,
    passed: true,
    is_human_reviewed: false,
    attempted_at: '2025-01-02T11:15:00Z',
    metadata: { duration_seconds: 35 },
    created_at: '2025-01-02T11:15:00Z',
    updated_at: '2025-01-02T11:15:00Z',
  },
] as const
