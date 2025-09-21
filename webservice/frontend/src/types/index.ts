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
  status: 'active' | 'inactive' | 'disabled' | 'ready' | 'error'
  message: string
  document_count: number
  embedding_model: string
  chunk_size: number
  auto_activated?: boolean
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

// Phase 3: Full Generation 관련 타입들
export type WorkflowState = 'idle' | 'parsing' | 'waiting_cli' | 'processing' | 'completed' | 'error'

export enum FullGenerationStatus {
  RECEIVED = 'received',
  ANALYZING_VCS = 'analyzing_vcs',
  GENERATING_SCENARIOS = 'generating_scenarios',
  GENERATING_WORD_DOC = 'generating_word_doc',
  GENERATING_EXCEL_LIST = 'generating_excel_list',
  GENERATING_BASE_SCENARIOS = 'generating_base_scenarios',
  MERGING_EXCEL = 'merging_excel',
  COMPLETED = 'completed',
  ERROR = 'error'
}

export interface FullGenerationProgressMessage {
  session_id: string
  status: FullGenerationStatus
  message: string
  progress: number
  current_step: string
  steps_completed: number
  total_steps: number
  details?: Record<string, unknown>
  result?: FullGenerationResultData
}

export interface FullGenerationResultData {
  session_id: string
  word_filename?: string
  excel_list_filename?: string
  base_scenario_filename?: string
  merged_excel_filename?: string
  download_urls: {
    word?: string
    excel_list?: string
    base_scenario?: string
    merged_excel?: string
    integrated_scenario?: string  // 새로운 통합 시나리오
    scenario?: string
    all?: string  // 일괄 다운로드 URL
  }
  generation_time?: number  // 생성 시간 (초)
  steps_completed?: number  // 완료된 단계 수
  total_steps?: number      // 전체 단계 수
  errors?: string[]         // 발생한 오류 목록
  warnings?: string[]       // 경고 메시지 목록
}

export interface ParseHtmlResponse {
  success: boolean
  data: Record<string, unknown>
  error: string | null
}

export interface SessionMetadata {
  title?: string
  content?: string
  parsed_data?: Record<string, unknown>
  user_name?: string
  [key: string]: unknown
}