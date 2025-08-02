import axios from 'axios'
import { scenarioApi, feedbackApi, ragApi, filesApi } from './api'

jest.mock('axios')
const mockedAxios = axios as jest.Mocked<typeof axios>

// Mock axios.create
mockedAxios.create = jest.fn(() => mockedAxios)
mockedAxios.interceptors = {
  response: {
    use: jest.fn()
  }
} as any

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
})