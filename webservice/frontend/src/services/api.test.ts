import axios from 'axios'
import { scenarioApi, feedbackApi, ragApi, filesApi } from './api'

jest.mock('axios')
const mockedAxios = axios as jest.Mocked<typeof axios>

// Mock axios.create
mockedAxios.create = jest.fn(() => mockedAxios)
mockedAxios.interceptors = {
  request: {
    use: jest.fn(),
    eject: jest.fn(),
    clear: jest.fn(),
    forEach: jest.fn()
  },
  response: {
    use: jest.fn(),
    eject: jest.fn(), 
    clear: jest.fn(),
    forEach: jest.fn()
  }
} as jest.Mocked<typeof axios.interceptors>

describe('API Services', () => {
  beforeEach(() => {
    jest.clearAllMocks()
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
      mockedAxios.post.mockResolvedValue(mockResponse)

      const request = {
        repo_path: '/test/repo',
        use_performance_mode: true
      }

      const result = await scenarioApi.generate(request)
      
      expect(mockedAxios.post).toHaveBeenCalledWith('/scenario/generate', request)
      expect(result).toEqual(mockResponse.data)
    })

    it('should get config', async () => {
      const mockConfig = {
        data: {
          model_name: 'qwen3:8b',
          timeout: 600
        }
      }
      mockedAxios.get.mockResolvedValue(mockConfig)

      const result = await scenarioApi.getConfig()
      
      expect(mockedAxios.get).toHaveBeenCalledWith('/scenario/config')
      expect(result).toEqual(mockConfig.data)
    })

    it('should generate WebSocket URL', () => {
      // Mock window.location
      Object.defineProperty(window, 'location', {
        value: {
          protocol: 'http:',
          host: 'localhost:3000'
        },
        writable: true
      })

      const url = scenarioApi.getWebSocketUrl()
      expect(url).toBe('ws://localhost:3000/api/scenario/generate-ws')
    })
  })

  describe('feedbackApi', () => {
    it('should submit feedback', async () => {
      const mockResponse = { data: { success: true } }
      mockedAxios.post.mockResolvedValue(mockResponse)

      const request = {
        feedback_type: 'like' as const,
        comments: 'Good scenario',
        testcase_feedback: [],
        repo_path: '/test/repo',
        git_analysis: 'analysis',
        scenario_content: {}
      }

      const result = await feedbackApi.submit(request)
      
      expect(mockedAxios.post).toHaveBeenCalledWith('/feedback/submit', request)
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
      mockedAxios.get.mockResolvedValue(mockStats)

      const result = await feedbackApi.getStats()
      
      expect(mockedAxios.get).toHaveBeenCalledWith('/feedback/stats')
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
      mockedAxios.get.mockResolvedValue(mockInfo)

      const result = await ragApi.getInfo()
      
      expect(mockedAxios.get).toHaveBeenCalledWith('/rag/info')
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
      mockedAxios.post.mockResolvedValue(mockResult)

      const result = await ragApi.indexDocuments(true)
      
      expect(mockedAxios.post).toHaveBeenCalledWith('/rag/index', { force_reindex: true })
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
      mockedAxios.post.mockResolvedValue(mockValidation)

      const result = await filesApi.validateRepoPath('/test/repo')
      
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/files/validate/repo-path', 
        '/test/repo',
        { headers: { 'Content-Type': 'application/json' } }
      )
      expect(result).toEqual(mockValidation.data)
    })

    it('should generate download URL', () => {
      const filename = 'test.xlsx'
      const url = filesApi.downloadExcelFile(filename)
      
      expect(url).toBe('/api/files/download/excel/test.xlsx')
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
      mockedAxios.get.mockResolvedValue(mockBackupFiles)

      const result = await feedbackApi.listBackupFiles()
      
      expect(mockedAxios.get).toHaveBeenCalledWith('/feedback/backup-files')
      expect(result).toEqual(mockBackupFiles.data)
    })

    it('should delete backup file', async () => {
      const mockResponse = {
        data: {
          message: '백업 파일이 성공적으로 삭제되었습니다.',
          success: true
        }
      }
      mockedAxios.delete.mockResolvedValue(mockResponse)

      const filename = 'feedback_backup_20240101_120000.json'
      const result = await feedbackApi.deleteBackupFile(filename)
      
      expect(mockedAxios.delete).toHaveBeenCalledWith('/feedback/backup-files/feedback_backup_20240101_120000.json')
      expect(result).toEqual(mockResponse.data)
    })

    it('should download backup file', async () => {
      const mockResponse = {
        data: new Blob(['{"test": "data"}'], { type: 'application/json' }),
        headers: { 'content-type': 'application/json' }
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const filename = 'feedback_backup_20240101_120000.json'
      const result = await feedbackApi.downloadBackupFile(filename)
      
      expect(mockedAxios.get).toHaveBeenCalledWith(
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
      mockedAxios.post.mockResolvedValue(mockReportData)

      const result = await feedbackApi.generateSummaryReport()
      
      expect(mockedAxios.post).toHaveBeenCalledWith('/feedback/summary-report')
      expect(result).toEqual(mockReportData.data)
    })

    it('should handle list backup files error', async () => {
      const errorMessage = 'Failed to list backup files'
      mockedAxios.get.mockRejectedValue(new Error(errorMessage))

      await expect(feedbackApi.listBackupFiles()).rejects.toThrow(errorMessage)
      expect(mockedAxios.get).toHaveBeenCalledWith('/feedback/backup-files')
    })

    it('should handle delete backup file error', async () => {
      const errorMessage = 'Failed to delete backup file'
      mockedAxios.delete.mockRejectedValue(new Error(errorMessage))

      const filename = 'feedback_backup_20240101_120000.json'
      await expect(feedbackApi.deleteBackupFile(filename)).rejects.toThrow(errorMessage)
      expect(mockedAxios.delete).toHaveBeenCalledWith('/feedback/backup-files/feedback_backup_20240101_120000.json')
    })

    it('should handle generate summary report error', async () => {
      const errorMessage = 'Failed to generate report'
      mockedAxios.post.mockRejectedValue(new Error(errorMessage))

      await expect(feedbackApi.generateSummaryReport()).rejects.toThrow(errorMessage)
      expect(mockedAxios.post).toHaveBeenCalledWith('/feedback/summary-report')
    })

    it('should properly encode filename with special characters', async () => {
      const mockResponse = { data: { success: true } }
      mockedAxios.delete.mockResolvedValue(mockResponse)

      const filenameWithSpecialChars = 'feedback_backup_2024-01-01_12:00:00.json'
      await feedbackApi.deleteBackupFile(filenameWithSpecialChars)
      
      expect(mockedAxios.delete).toHaveBeenCalledWith('/feedback/backup-files/feedback_backup_2024-01-01_12%3A00%3A00.json')
    })
  })
})