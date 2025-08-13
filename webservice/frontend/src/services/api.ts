import axios from 'axios';
import type {
  ScenarioGenerationRequest,
  ScenarioResponse,
  FeedbackRequest,
  FeedbackStats,
  RAGInfo,
  RAGStatus,
  IndexingResult,
} from '../types';
import logger from '../utils/logger';

// Create Axios instance
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API response interceptor for logging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    logger.error('API Error:', error, {
      config: error.config,
      response: error.response?.data,
    });
    return Promise.reject(error);
  }
);

// Scenario Generation API
export const scenarioApi = {
  generate: async (request: ScenarioGenerationRequest): Promise<ScenarioResponse> => {
    const response = await api.post('/scenario/generate', request);
    return response.data;
  },

  getConfig: async () => {
    const response = await api.get('/scenario/config');
    return response.data;
  },

  getWebSocketUrl: () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = import.meta.env.DEV ? '8000' : window.location.port;
    const url = `${protocol}//${host}:${port}/api/scenario/generate-ws`;
    logger.info(`Generated WebSocket URL: ${url}`);
    return url;
  }
};

// Feedback API
export const feedbackApi = {
  submit: async (request: FeedbackRequest) => {
    const response = await api.post('/feedback/submit', request);
    return response.data;
  },

  getStats: async (): Promise<FeedbackStats> => {
    const response = await api.get('/feedback/stats');
    return response.data;
  },

  getInsights: async () => {
    const response = await api.get('/feedback/insights');
    return response.data;
  },

  getPromptEnhancement: async () => {
    const response = await api.get('/feedback/prompt-enhancement');
    return response.data;
  },

  getExamples: async (category: string, limit: number = 5) => {
    const response = await api.get(`/feedback/examples/${category}?limit=${limit}`);
    return response.data;
  },

  exportData: async () => {
    const response = await api.get('/feedback/export');
    return response.data;
  },

  resetAll: async (createBackup: boolean = true) => {
    const response = await api.delete(`/feedback/reset/all?create_backup=${createBackup}`);
    return response.data;
  },

  resetByCategory: async (category: string, createBackup: boolean = true) => {
    const response = await api.delete(`/feedback/reset/category/${category}?create_backup=${createBackup}`);
    return response.data;
  },

  resetCache: async () => {
    const response = await api.post('/feedback/cache/reset');
    return response.data;
  },

  // 새로운 백업 파일 관리 API
  listBackupFiles: async () => {
    const response = await api.get('/feedback/backup-files');
    return response.data;
  },

  deleteBackupFile: async (filename: string) => {
    const response = await api.delete(`/feedback/backup-files/${encodeURIComponent(filename)}`);
    return response.data;
  },

  downloadBackupFile: async (filename: string) => {
    const response = await api.get(`/feedback/backup-files/${encodeURIComponent(filename)}/download`, {
      responseType: 'blob'
    });
    return response;
  },

  generateSummaryReport: async () => {
    const response = await api.post('/feedback/summary-report');
    return response.data;
  }
};

// RAG System API
export const ragApi = {
  getInfo: async (): Promise<RAGInfo> => {
    const response = await api.get('/rag/info');
    return response.data;
  },

  getStatus: async (): Promise<RAGStatus> => {
    const response = await api.get('/rag/status');
    return response.data;
  },

  indexDocuments: async (forceReindex: boolean = false): Promise<IndexingResult> => {
    const response = await api.post('/rag/index', { force_reindex: forceReindex });
    return response.data;
  },

  clearDatabase: async () => {
    const response = await api.delete('/rag/clear');
    return response.data;
  },

  getDocumentsInfo: async () => {
    const response = await api.get('/rag/documents/info');
    return response.data;
  },

  getAutoActivationStatus: async () => {
    const response = await api.get('/rag/auto-activation');
    return response.data;
  },

  debugSystem: async () => {
    const response = await api.get('/rag/debug');
    return response.data;
  }
};

// File Handling API
export const filesApi = {
  validateRepoPath: async (repoPath: string) => {
    const response = await api.post('/files/validate/repo-path', {
      repo_path: repoPath,
    });
    return response.data;
  },

  listOutputFiles: async () => {
    const response = await api.get('/files/list/outputs');
    return response.data;
  },

  downloadExcelFile: (filename: string) => {
    const encodedFilename = encodeURIComponent(filename);
    return `/api/files/download/excel/${encodedFilename}`;
  },

  deleteOutputFile: async (filename: string) => {
    const response = await api.delete(`/files/outputs/${encodeURIComponent(filename)}`);
    return response.data;
  },

  uploadFile: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

// v2 API (CLI 연동용)
export const v2Api = {
  /**
   * CLI에서 시나리오 생성을 요청하는 API
   */
  generateScenario: async (clientId: string, repoPath: string, usePerformanceMode: boolean = true) => {
    const response = await api.post('/v2/scenario/generate', {
      client_id: clientId,
      repo_path: repoPath,
      use_performance_mode: usePerformanceMode
    });
    return response.data;
  },

  /**
   * 특정 클라이언트의 생성 상태 조회
   */
  getGenerationStatus: async (clientId: string) => {
    const response = await api.get(`/v2/scenario/status/${clientId}`);
    return response.data;
  },

  /**
   * v2 WebSocket URL 생성
   */
  getWebSocketUrl: (clientId: string) => {
    const baseUrl = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NODE_ENV === 'development' ? 'localhost:8000' : window.location.host;
    return `${baseUrl}//${host}/api/v2/ws/progress/${clientId}`;
  }
};

export default api;
