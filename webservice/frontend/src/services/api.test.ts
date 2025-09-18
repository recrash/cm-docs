import { vi } from 'vitest'

// Mock axios completely before any imports
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn(),
        eject: vi.fn(),
        clear: vi.fn(),
        forEach: vi.fn()
      },
      response: {
        use: vi.fn(),
        eject: vi.fn(), 
        clear: vi.fn(),
        forEach: vi.fn()
      }
    }
  }

  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      ...mockAxiosInstance
    }
  }
})

// Now import everything after mocking
import axios from 'axios'
import { scenarioApi, feedbackApi, ragApi, filesApi, v2Api } from './api'

// Get the mock instance for tests
const mockAxiosInstance = (axios as any).create()

describe('API Services', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('scenarioApi', () => {
    it('should generate scenario', async () => {
      const mockResponse = {
        data: {
          scenario_description: 'Test scenario',
          test_scenario_name: 'Test name',
          test_cases: []
        }
      }
      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const request = {
        repo_path: '/test/repo',
        use_performance_mode: true
      }

      const result = await scenarioApi.generate(request)
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/scenario/generate', request)
      expect(result).toEqual(mockResponse.data)
    })

    it('should get config', async () => {
      const mockConfig = {
        data: {
          model_name: 'qwen3:8b',
          timeout: 600
        }
      }
      mockAxiosInstance.get.mockResolvedValue(mockConfig)

      const result = await scenarioApi.getConfig()
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/scenario/config')
      expect(result).toEqual(mockConfig.data)
    })

    it('should generate WebSocket URL', () => {
      // Mock window.location with hostname property
      Object.defineProperty(window, 'location', {
        value: {
          protocol: 'http:',
          hostname: 'localhost',
          port: '3000'
        },
        writable: true
      })

      // Mock import.meta.env.DEV for development mode
      vi.stubEnv('DEV', true)

      const url = scenarioApi.getWebSocketUrl()
      expect(url).toBe('ws://localhost:8000/api/webservice/scenario/generate-ws')
    })
  })

  describe('feedbackApi', () => {
    it('should submit feedback', async () => {
      const mockResponse = { data: { success: true } }
      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const request = {
        feedback_type: 'like' as const,
        comments: 'Good scenario',
        testcase_feedback: [],
        repo_path: '/test/repo',
        git_analysis: 'analysis',
        scenario_content: {}
      }

      const result = await feedbackApi.submit(request)
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/feedback/submit', request)
      expect(result).toEqual(mockResponse.data)
    })

    it('should get feedback stats', async () => {
      const mockStats = {
        data: {
          total_feedback: 10,
          category_distribution: { good: 7, bad: 3 },
          average_scores: { overall: 4.2 }
        }
      }
      mockAxiosInstance.get.mockResolvedValue(mockStats)

      const result = await feedbackApi.getStats()
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/feedback/stats')
      expect(result).toEqual(mockStats.data)
    })
  })

  describe('ragApi', () => {
    it('should get RAG info', async () => {
      const mockInfo = {
        data: {
          chroma_info: { count: 100 },
          chunk_size: 1000,
          documents: { enabled: true }
        }
      }
      mockAxiosInstance.get.mockResolvedValue(mockInfo)

      const result = await ragApi.getInfo()
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/rag/info')
      expect(result).toEqual(mockInfo.data)
    })

    it('should index documents', async () => {
      const mockResult = {
        data: {
          status: 'success',
          indexed_count: 5,
          total_chunks_added: 50
        }
      }
      mockAxiosInstance.post.mockResolvedValue(mockResult)

      const result = await ragApi.indexDocuments(true)
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/rag/index', { force_reindex: true })
      expect(result).toEqual(mockResult.data)
    })
  })

  describe('filesApi', () => {
    it('should validate repo path', async () => {
      const mockValidation = {
        data: {
          valid: true,
          message: 'Valid repository'
        }
      }
      mockAxiosInstance.post.mockResolvedValue(mockValidation)

      const result = await filesApi.validateRepoPath('/test/repo')
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/files/validate/repo-path', 
        { repo_path: '/test/repo' }
      )
      expect(result).toEqual(mockValidation.data)
    })

    it('should generate download URL', () => {
      const filename = 'test.xlsx'
      const url = filesApi.downloadExcelFile(filename)
      
      expect(url).toBe('/api/webservice/files/download/excel/test.xlsx')
    })
  })

  describe('feedbackApi - New Backup Management Functions', () => {
    it('should list backup files', async () => {
      const mockBackupFiles = {
        data: {
          files: [
            {
              filename: 'feedback_backup_20240101_120000.json',
              size: 1024,
              created_at: '2024-01-01T12:00:00',
              modified_at: '2024-01-01T12:00:00'
            }
          ]
        }
      }
      mockAxiosInstance.get.mockResolvedValue(mockBackupFiles)

      const result = await feedbackApi.listBackupFiles()
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/feedback/backup-files')
      expect(result).toEqual(mockBackupFiles.data)
    })

    it('should delete backup file', async () => {
      const mockResponse = {
        data: {
          message: '백업 파일이 성공적으로 삭제되었습니다.',
          success: true
        }
      }
      mockAxiosInstance.delete.mockResolvedValue(mockResponse)

      const filename = 'feedback_backup_20240101_120000.json'
      const result = await feedbackApi.deleteBackupFile(filename)
      
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/feedback/backup-files/feedback_backup_20240101_120000.json')
      expect(result).toEqual(mockResponse.data)
    })

    it('should download backup file', async () => {
      const mockResponse = {
        data: new Blob(['{"test": "data"}'], { type: 'application/json' }),
        headers: { 'content-type': 'application/json' }
      }
      mockAxiosInstance.get.mockResolvedValue(mockResponse)

      const filename = 'feedback_backup_20240101_120000.json'
      const result = await feedbackApi.downloadBackupFile(filename)
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/feedback/backup-files/feedback_backup_20240101_120000.json/download',
        { responseType: 'blob' }
      )
      expect(result).toEqual(mockResponse)
    })

    it('should generate summary report', async () => {
      const mockReportData = {
        data: {
          report_data: {
            generated_at: '2024-01-01T12:00:00',
            summary: {
              total_feedback: 10,
              category_distribution: { good: 7, bad: 3 },
              average_scores: { overall: 4.2 }
            },
            insights: {
              negative_feedback_count: 3,
              common_issues: ['정확성 부족'],
              improvement_suggestions: ['더 상세한 분석 필요']
            },
            report_metadata: {
              report_type: 'feedback_summary',
              report_version: '1.0',
              data_period: '전체 기간'
            }
          },
          filename: 'feedback_summary_report_20240101_120000.json',
          success: true
        }
      }
      mockAxiosInstance.post.mockResolvedValue(mockReportData)

      const result = await feedbackApi.generateSummaryReport()
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/feedback/summary-report')
      expect(result).toEqual(mockReportData.data)
    })

    it('should handle list backup files error', async () => {
      const errorMessage = 'Failed to list backup files'
      mockAxiosInstance.get.mockRejectedValue(new Error(errorMessage))

      await expect(feedbackApi.listBackupFiles()).rejects.toThrow(errorMessage)
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/feedback/backup-files')
    })

    it('should handle delete backup file error', async () => {
      const errorMessage = 'Failed to delete backup file'
      mockAxiosInstance.delete.mockRejectedValue(new Error(errorMessage))

      const filename = 'feedback_backup_20240101_120000.json'
      await expect(feedbackApi.deleteBackupFile(filename)).rejects.toThrow(errorMessage)
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/feedback/backup-files/feedback_backup_20240101_120000.json')
    })

    it('should handle generate summary report error', async () => {
      const errorMessage = 'Failed to generate report'
      mockAxiosInstance.post.mockRejectedValue(new Error(errorMessage))

      await expect(feedbackApi.generateSummaryReport()).rejects.toThrow(errorMessage)
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/feedback/summary-report')
    })

    it('should properly encode filename with special characters', async () => {
      const mockResponse = { data: { success: true } }
      mockAxiosInstance.delete.mockResolvedValue(mockResponse)

      const filenameWithSpecialChars = 'feedback_backup_2024-01-01_12:00:00.json'
      await feedbackApi.deleteBackupFile(filenameWithSpecialChars)
      
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/feedback/backup-files/feedback_backup_2024-01-01_12%3A00%3A00.json')
    })
  })

  describe('v2Api', () => {
    it('should prepare session with metadata', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: '세션이 성공적으로 준비되었습니다.'
        }
      }
      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const sessionId = 'test-session-123'
      const metadata = {
        title: 'Test Document',
        content: 'Test content',
        parsed_data: {}
      }

      const result = await v2Api.prepareSession(sessionId, metadata)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/v2/prepare-session', {
        session_id: sessionId,
        metadata_json: metadata
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should generate v2 scenario', async () => {
      const mockResponse = {
        data: {
          success: true,
          client_id: 'test-client-123'
        }
      }
      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const clientId = 'test-client-123'
      const repoPath = '/test/repo'
      const usePerformanceMode = true

      const result = await v2Api.generateScenario(clientId, repoPath, usePerformanceMode)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/v2/scenario/generate', {
        client_id: clientId,
        repo_path: repoPath,
        use_performance_mode: usePerformanceMode
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should get generation status', async () => {
      const mockStatus = {
        data: {
          status: 'completed',
          progress: 100,
          message: '생성 완료'
        }
      }
      mockAxiosInstance.get.mockResolvedValue(mockStatus)

      const clientId = 'test-client-123'
      const result = await v2Api.getGenerationStatus(clientId)

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(`/v2/scenario/status/${clientId}`)
      expect(result).toEqual(mockStatus.data)
    })

    it('should init full generation session', async () => {
      const mockResponse = {
        data: {
          success: true,
          session_id: 'test-session-123'
        }
      }
      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const sessionId = 'test-session-123'
      const result = await v2Api.initFullGenerationSession(sessionId)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(`/v2/init-session/${sessionId}`)
      expect(result).toEqual(mockResponse.data)
    })

    it('should generate WebSocket URLs correctly', () => {
      // Mock window.location for development mode
      Object.defineProperty(window, 'location', {
        value: {
          protocol: 'http:',
          hostname: 'localhost',
          host: 'localhost:3000'
        },
        writable: true
      })

      // Mock import.meta.env.DEV for development mode
      vi.stubEnv('DEV', true)

      const clientId = 'test-client-123'
      const sessionId = 'test-session-123'

      const v2Url = v2Api.getWebSocketUrl(clientId)
      const fullGenUrl = v2Api.getFullGenerationWebSocketUrl(sessionId)

      expect(v2Url).toBe('ws://localhost:8000/api/webservice/v2/ws/progress/test-client-123')
      expect(fullGenUrl).toBe('ws://localhost:8000/api/webservice/v2/ws/full-generation/test-session-123')
    })
  })
})