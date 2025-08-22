import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import FeedbackAnalysisTab from './FeedbackAnalysisTab'
import { feedbackApi } from '../services/api'

// Mock the feedbackApi
jest.mock('../services/api', () => ({
  feedbackApi: {
    getStats: jest.fn(),
    getInsights: jest.fn(),
    getPromptEnhancement: jest.fn(),
    getExamples: jest.fn(),
    exportData: jest.fn(),
    resetAll: jest.fn(),
    resetByCategory: jest.fn(),
    generateSummaryReport: jest.fn(),
  }
}))

// Mock the BackupFileManagementModal component
jest.mock('./BackupFileManagementModal', () => {
  return function MockBackupFileManagementModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    return open ? (
      <div data-testid="backup-modal">
        <h2>백업 파일 관리</h2>
        <button onClick={onClose}>닫기</button>
      </div>
    ) : null
  }
})

// Mock window.alert and window.confirm
global.alert = jest.fn()
global.confirm = jest.fn()

// Mock URL methods for file download
global.URL.createObjectURL = jest.fn(() => 'mock-url')
global.URL.revokeObjectURL = jest.fn()

// Mock document.createElement and appendChild/removeChild for file download
const mockLink = {
  href: '',
  download: '',
  click: jest.fn(),
}
document.createElement = jest.fn().mockImplementation((tagName) => {
  if (tagName === 'a') {
    return mockLink
  }
  return {}
})
document.body.appendChild = jest.fn()
document.body.removeChild = jest.fn()

describe('FeedbackAnalysisTab - Data Management', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks()
    
    // Mock default API responses
    ;(feedbackApi.getStats as jest.Mock).mockResolvedValue({
      total_feedback: 10,
      category_distribution: { good: 7, bad: 3, neutral: 0 },
      average_scores: { overall: 4.2, usefulness: 4.0, accuracy: 4.1, completeness: 4.3 }
    })
    
    ;(feedbackApi.getInsights as jest.Mock).mockResolvedValue({
      negative_feedback_count: 3,
      common_issues: ['정확성 부족'],
      improvement_suggestions: ['더 상세한 분석 필요']
    })
    
    ;(feedbackApi.getPromptEnhancement as jest.Mock).mockResolvedValue({
      is_active: true,
      enhancement_summary: {
        feedback_count: 5,
        improvement_areas: ['accuracy'],
        good_examples_available: 3,
        bad_examples_available: 2
      }
    })
    
    ;(feedbackApi.getExamples as jest.Mock).mockResolvedValue({
      examples: []
    })
  })

  it('should render 3 action buttons in data management section', async () => {
    render(<FeedbackAnalysisTab />)
    
    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText('💾 데이터 관리')).toBeInTheDocument()
    })
    
    // Check if all 3 buttons are rendered
    expect(screen.getByText('📥 피드백 데이터 내보내기')).toBeInTheDocument()
    expect(screen.getByText('📋 백업 파일 관리')).toBeInTheDocument()
    expect(screen.getByText('📊 요약 보고서')).toBeInTheDocument()
  })

  it('should handle export data button click', async () => {
    (feedbackApi.exportData as jest.Mock).mockResolvedValue({
      message: '데이터가 성공적으로 내보내졌습니다.',
      filename: 'feedback_export_test.json'
    })
    
    render(<FeedbackAnalysisTab />)
    
    await waitFor(() => {
      expect(screen.getByText('📥 피드백 데이터 내보내기')).toBeInTheDocument()
    })
    
    const exportButton = screen.getByText('📥 피드백 데이터 내보내기')
    fireEvent.click(exportButton)
    
    await waitFor(() => {
      expect(feedbackApi.exportData).toHaveBeenCalledTimes(1)
      expect(global.alert).toHaveBeenCalledWith('피드백 데이터가 성공적으로 내보내졌습니다.')
    })
  })

  it('should open backup management modal when clicking backup button', async () => {
    render(<FeedbackAnalysisTab />)
    
    await waitFor(() => {
      expect(screen.getByText('📋 백업 파일 관리')).toBeInTheDocument()
    })
    
    const backupButton = screen.getByText('📋 백업 파일 관리')
    fireEvent.click(backupButton)
    
    // Check if modal is opened
    expect(screen.getByTestId('backup-modal')).toBeInTheDocument()
    expect(screen.getByText('백업 파일 관리')).toBeInTheDocument()
  })

  it('should close backup management modal when clicking close button', async () => {
    render(<FeedbackAnalysisTab />)
    
    await waitFor(() => {
      expect(screen.getByText('📋 백업 파일 관리')).toBeInTheDocument()
    })
    
    // Open modal
    const backupButton = screen.getByText('📋 백업 파일 관리')
    fireEvent.click(backupButton)
    
    expect(screen.getByTestId('backup-modal')).toBeInTheDocument()
    
    // Close modal
    const closeButton = screen.getByText('닫기')
    fireEvent.click(closeButton)
    
    expect(screen.queryByTestId('backup-modal')).not.toBeInTheDocument()
  })

  it('should handle generate summary report button click', async () => {
    const mockReportData = {
      report_data: {
        generated_at: '2024-01-01T12:00:00',
        summary: {
          total_feedback: 10,
          category_distribution: { good: 7, bad: 3 },
          average_scores: { overall: 4.2 }
        }
      },
      filename: 'feedback_summary_report_20240101_120000.json',
      success: true
    }
    
    ;(feedbackApi.generateSummaryReport as jest.Mock).mockResolvedValue(mockReportData)
    
    render(<FeedbackAnalysisTab />)
    
    await waitFor(() => {
      expect(screen.getByText('📊 요약 보고서')).toBeInTheDocument()
    })
    
    const reportButton = screen.getByText('📊 요약 보고서')
    fireEvent.click(reportButton)
    
    await waitFor(() => {
      expect(feedbackApi.generateSummaryReport).toHaveBeenCalledTimes(1)
      expect(global.URL.createObjectURL).toHaveBeenCalled()
      expect(mockLink.download).toBe(mockReportData.filename)
      expect(mockLink.click).toHaveBeenCalled()
      expect(global.alert).toHaveBeenCalledWith('요약 보고서가 성공적으로 생성되었습니다.')
    })
  })

  it('should handle export data error', async () => {
    (feedbackApi.exportData as jest.Mock).mockRejectedValue(new Error('Export failed'))
    
    render(<FeedbackAnalysisTab />)
    
    await waitFor(() => {
      expect(screen.getByText('📥 피드백 데이터 내보내기')).toBeInTheDocument()
    })
    
    const exportButton = screen.getByText('📥 피드백 데이터 내보내기')
    fireEvent.click(exportButton)
    
    await waitFor(() => {
      expect(feedbackApi.exportData).toHaveBeenCalledTimes(1)
      expect(global.alert).toHaveBeenCalledWith('데이터 내보내기 중 오류가 발생했습니다.')
    })
  })

  it('should handle generate report error', async () => {
    (feedbackApi.generateSummaryReport as jest.Mock).mockRejectedValue(new Error('Report generation failed'))
    
    render(<FeedbackAnalysisTab />)
    
    await waitFor(() => {
      expect(screen.getByText('📊 요약 보고서')).toBeInTheDocument()
    })
    
    const reportButton = screen.getByText('📊 요약 보고서')
    fireEvent.click(reportButton)
    
    await waitFor(() => {
      expect(feedbackApi.generateSummaryReport).toHaveBeenCalledTimes(1)
      expect(global.alert).toHaveBeenCalledWith('요약 보고서 생성 중 오류가 발생했습니다.')
    })
  })

  it('should display proper button layout on different screen sizes', async () => {
    render(<FeedbackAnalysisTab />)
    
    await waitFor(() => {
      expect(screen.getByText('📥 피드백 데이터 내보내기')).toBeInTheDocument()
    })
    
    // Check if buttons are in proper Grid layout
    const dataManagementSection = screen.getByText('데이터 백업 및 관리').closest('div')
    expect(dataManagementSection).toBeInTheDocument()
    
    // All 3 buttons should be present
    const buttons = [
      screen.getByText('📥 피드백 데이터 내보내기'),
      screen.getByText('📋 백업 파일 관리'),
      screen.getByText('📊 요약 보고서')
    ]
    
    buttons.forEach(button => {
      expect(button).toBeInTheDocument()
      expect(button.closest('.MuiGrid-item')).toBeInTheDocument()
    })
  })

  it('should handle feedback reset operations with proper confirmation', async () => {
    (global.confirm as jest.Mock).mockReturnValue(true)
    ;(feedbackApi.resetAll as jest.Mock).mockResolvedValue({
      message: '모든 피드백이 성공적으로 삭제되었습니다.',
      success: true
    })
    
    render(<FeedbackAnalysisTab />)
    
    await waitFor(() => {
      expect(screen.getByText('전체 피드백 삭제')).toBeInTheDocument()
    })
    
    const deleteButton = screen.getByText('전체 피드백 삭제')
    fireEvent.click(deleteButton)
    
    await waitFor(() => {
      expect(global.confirm).toHaveBeenCalledWith('모든 피드백을 삭제하시겠습니까? (백업이 자동으로 생성됩니다)')
      expect(feedbackApi.resetAll).toHaveBeenCalledWith(true)
      expect(global.alert).toHaveBeenCalledWith('피드백이 성공적으로 삭제되었습니다.')
    })
  })
})