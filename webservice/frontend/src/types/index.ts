// API 관련 타입 정의

export interface TestCase {
  ID: string
  절차: string
  사전조건: string
  데이터: string
  예상결과: string
  Unit?: string
  Integration?: string
}

export interface ScenarioResponse {
  scenario_description: string
  test_scenario_name: string
  test_cases: TestCase[]
  metadata?: {
    llm_response_time: number
    prompt_size: number
    added_chunks: number
    excel_filename: string
  }
}

export interface ScenarioGenerationRequest {
  repo_path: string
  use_performance_mode: boolean
}

export const GenerationStatus = {
  STARTED: 'started',
  ANALYZING_GIT: 'analyzing_git',
  STORING_RAG: 'storing_rag',
  CALLING_LLM: 'calling_llm',
  PARSING_RESPONSE: 'parsing_response',
  GENERATING_EXCEL: 'generating_excel',
  COMPLETED: 'completed',
  ERROR: 'error'
} as const

export type GenerationStatusType = typeof GenerationStatus[keyof typeof GenerationStatus]

export interface GenerationProgress {
  status: GenerationStatusType
  message: string
  progress: number
  details?: Record<string, unknown>
}

export interface FeedbackRequest {
  feedback_type: 'like' | 'dislike'
  comments?: string
  testcase_feedback: TestCaseFeedback[]
  repo_path: string
  git_analysis: string
  scenario_content: Record<string, unknown>
}

export interface TestCaseFeedback {
  testcase_id: string
  score: number
  comments?: string
}

export interface FeedbackStats {
  total_feedback: number
  category_distribution: { [key: string]: number }
  average_scores: { [key: string]: number }
}

export interface RAGInfo {
  chroma_info: {
    count: number
    embedding_model: string
  }
  chunk_size: number
  documents: {
    enabled: boolean
    folder_path?: string
    supported_files: number
    total_files: number
    file_types: { [key: string]: number }
  }
}

export interface RAGStatus {
  status: 'active' | 'inactive' | 'error'
  message: string
  document_count: number
  embedding_model: string
  chunk_size: number
}

export interface IndexingResult {
  status: string
  indexed_count: number
  total_chunks_added: number
  message?: string
}

export interface PromptEnhancement {
  is_active?: boolean
  enhancement_summary?: {
    feedback_count?: number
    improvement_areas?: unknown[]
    good_examples_available?: number
    bad_examples_available?: number
  }
}

export interface ExampleItem {
  test_scenario_name?: string
  timestamp?: string
  overall_score?: number
  comments?: string
  scenario_content?: {
    test_scenario_name?: string
    [key: string]: unknown
  }
  [key: string]: unknown
}

export interface V2ResultData {
  description?: string
  filename?: string
  test_scenario_name?: string
  test_cases?: TestCase[]
  llm_response_time?: number
  prompt_size?: number
  added_chunks?: number
}