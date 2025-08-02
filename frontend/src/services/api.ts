import axios from 'axios'
import type {
  ScenarioGenerationRequest,
  ScenarioResponse,
  FeedbackRequest,
  FeedbackStats,
  RAGInfo,
  RAGStatus,
  IndexingResult
} from '../types'

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// API 응답 인터셉터
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 시나리오 생성 API
export const scenarioApi = {
  generate: async (request: ScenarioGenerationRequest): Promise<ScenarioResponse> => {
    const response = await api.post('/scenario/generate', request)
    return response.data
  },

  getConfig: async () => {
    const response = await api.get('/scenario/config')
    return response.data
  },

  // WebSocket 연결을 위한 URL 생성
  getWebSocketUrl: () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    // 개발 환경에서는 백엔드 포트 8000으로 직접 연결
    const port = process.env.NODE_ENV === 'production' ? window.location.port : '8000'
    return `${protocol}//${host}:${port}/api/scenario/generate-ws`
  }
}

// 피드백 API
export const feedbackApi = {
  submit: async (request: FeedbackRequest) => {
    const response = await api.post('/feedback/submit', request)
    return response.data
  },

  getStats: async (): Promise<FeedbackStats> => {
    const response = await api.get('/feedback/stats')
    return response.data
  },

  getExamples: async (category: 'good' | 'bad' | 'neutral', limit: number = 5) => {
    const response = await api.get(`/feedback/examples/${category}?limit=${limit}`)
    return response.data
  },

  getInsights: async () => {
    const response = await api.get('/feedback/insights')
    return response.data
  },

  getPromptEnhancement: async () => {
    const response = await api.get('/feedback/prompt-enhancement')
    return response.data
  },

  getEnhancementPreview: async () => {
    const response = await api.get('/feedback/prompt-enhancement/preview')
    return response.data
  },

  exportData: async () => {
    const response = await api.get('/feedback/export')
    return response.data
  },

  getCategoryCount: async () => {
    const response = await api.get('/feedback/count-by-category')
    return response.data
  },

  resetAll: async (createBackup: boolean = true) => {
    const response = await api.delete(`/feedback/reset/all?create_backup=${createBackup}`)
    return response.data
  },

  resetByCategory: async (category: 'good' | 'bad' | 'neutral', createBackup: boolean = true) => {
    const response = await api.delete(`/feedback/reset/category/${category}?create_backup=${createBackup}`)
    return response.data
  }
}

// RAG 시스템 API
export const ragApi = {
  getInfo: async (): Promise<RAGInfo> => {
    const response = await api.get('/rag/info')
    return response.data
  },

  getStatus: async (): Promise<RAGStatus> => {
    const response = await api.get('/rag/status')
    return response.data
  },

  indexDocuments: async (forceReindex: boolean = false): Promise<IndexingResult> => {
    const response = await api.post('/rag/index', { force_reindex: forceReindex })
    return response.data
  },

  clearDatabase: async () => {
    const response = await api.delete('/rag/clear')
    return response.data
  },

  getDocumentsInfo: async () => {
    const response = await api.get('/rag/documents/info')
    return response.data
  }
}

// 파일 처리 API
export const filesApi = {
  validateRepoPath: async (repoPath: string) => {
    const response = await api.post('/files/validate/repo-path', {
      repo_path: repoPath
    })
    return response.data
  },

  listOutputFiles: async () => {
    const response = await api.get('/files/list/outputs')
    return response.data
  },

  downloadExcelFile: (filename: string) => {
    // URL encode the filename to handle Korean characters properly
    const encodedFilename = encodeURIComponent(filename)
    return `/api/files/download/excel/${encodedFilename}`
  },

  deleteOutputFile: async (filename: string) => {
    const response = await api.delete(`/files/outputs/${filename}`)
    return response.data
  },

  uploadFile: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }
}

export default api