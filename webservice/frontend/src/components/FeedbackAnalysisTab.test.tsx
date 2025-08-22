import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import React from 'react'
import FeedbackAnalysisTab from './FeedbackAnalysisTab'

// Mock the feedbackApi
vi.mock('../services/api', () => ({
  feedbackApi: {
    getStats: vi.fn().mockResolvedValue({
      total_feedback: 0,
      category_distribution: {},
      average_scores: {}
    }),
    getInsights: vi.fn().mockResolvedValue({
      negative_feedback_count: 0,
      common_issues: [],
      improvement_suggestions: []
    }),
    getPromptEnhancement: vi.fn().mockResolvedValue({
      is_active: false
    }),
    getExamples: vi.fn().mockResolvedValue({ examples: [] }),
    exportData: vi.fn(),
    resetAll: vi.fn(),
    resetByCategory: vi.fn(),
    generateSummaryReport: vi.fn(),
    listBackupFiles: vi.fn(),
    deleteBackupFile: vi.fn(),
    downloadBackupFile: vi.fn(),
    exportFeedback: vi.fn(),
    resetFeedback: vi.fn(),
  }
}))

// Mock the BackupFileManagementModal component
vi.mock('./BackupFileManagementModal', () => ({
  default: function MockBackupFileManagementModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    return open ? (
      <div data-testid="backup-modal">
        <h2>백업 파일 관리</h2>
        <button onClick={onClose}>닫기</button>
      </div>
    ) : null
  }
}))

describe('FeedbackAnalysisTab', () => {
  it('renders data management section', async () => {
    render(<FeedbackAnalysisTab />)
    
    // Wait for the component to load and render after async operations
    await waitFor(() => {
      expect(screen.getByText('📊 피드백 분석 대시보드')).toBeInTheDocument()
    })
    
    expect(screen.getByText('💾 데이터 관리')).toBeInTheDocument()
  })

  it('shows no feedback message when no feedback exists', async () => {
    render(<FeedbackAnalysisTab />)
    
    // Wait for the loading to complete and no feedback message to appear
    await waitFor(() => {
      expect(screen.getByText('아직 수집된 피드백이 없습니다. 시나리오를 생성하고 평가를 남겨주세요!')).toBeInTheDocument()
    })
  })

  it('renders action buttons in data management section', async () => {
    render(<FeedbackAnalysisTab />)
    
    // Wait for the component to fully load
    await waitFor(() => {
      expect(screen.getByText('📊 피드백 분석 대시보드')).toBeInTheDocument()
    })
    
    expect(screen.getByText('📥 피드백 데이터 내보내기')).toBeInTheDocument()
    expect(screen.getByText('📋 백업 파일 관리')).toBeInTheDocument()
    expect(screen.getByText('📊 요약 보고서')).toBeInTheDocument()
  })
})