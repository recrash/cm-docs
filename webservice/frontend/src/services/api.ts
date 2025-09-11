import axios from 'axios';
import type {
  ScenarioGenerationRequest,
  ScenarioResponse,
  FeedbackRequest,
  FeedbackStats,
  RAGInfo,
  RAGStatus,
  IndexingResult,
  ParseHtmlResponse,
} from '../types';
import logger from '../utils/logger';

// Create Axios instance with dynamic base URL
const api = axios.create({
  baseURL: `${import.meta.env.BASE_URL}api/webservice`,
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
    const basePath = import.meta.env.BASE_URL.replace(/\/$/, '');
    const url = `${protocol}//${host}:${port}${basePath}/api/webservice/scenario/generate-ws`;
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
    return `${import.meta.env.BASE_URL}api/webservice/files/download/excel/${encodedFilename}`;
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

// AutoDoc Service API (Phase 3)
export const autodocApi = {
  parseHtmlOnly: async (file: File): Promise<ParseHtmlResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(
        `${window.location.protocol}//${window.location.hostname}:${window.location.port}/api/autodoc/parse-html-only`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 30000,
        }
      );
      return response.data;
    } catch (error) {
      logger.error('HTML parsing failed:', error as Error);
      throw new Error('HTML 파일 파싱에 실패했습니다.');
    }
  },

  // 3개 문서 일괄 다운로드
  downloadAll: async (downloadUrls: Record<string, string>): Promise<void> => {
    const downloads = [];
    
    // Word 문서 다운로드
    if (downloadUrls.word) {
      downloads.push({
        url: downloadUrls.word,
        filename: '변경관리_요청서.docx'
      });
    }
    
    // Excel 목록 다운로드
    if (downloadUrls.excel_list) {
      downloads.push({
        url: downloadUrls.excel_list,
        filename: '변경요청_목록.xlsx'
      });
    }
    
    // 기본 시나리오 다운로드
    if (downloadUrls.base_scenario) {
      downloads.push({
        url: downloadUrls.base_scenario,
        filename: '테스트_시나리오.xlsx'
      });
    }
    
    // 순차적으로 다운로드 실행
    for (const item of downloads) {
      const link = document.createElement('a');
      link.href = item.url;
      link.download = item.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // 다운로드 간 약간의 딜레이
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }
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
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.DEV ? 'localhost:8000' : window.location.host;
    const basePath = import.meta.env.BASE_URL.replace(/\/$/, '');
    return `${protocol}//${host}${basePath}/api/webservice/v2/ws/progress/${clientId}`;
  }
};

export default api;
