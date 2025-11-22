import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Alert,
  CircularProgress,
  Paper,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material'
import {
  ExpandMore,
  Download,
  Delete,
  TrendingUp,
  TrendingDown,
  FolderOpen,
  Assessment
} from '@mui/icons-material'
import { feedbackApi } from '../services/api'
import type { FeedbackStats, PromptEnhancement, ExampleItem } from '../types'
import BackupFileManagementModal from './BackupFileManagementModal'

export default function FeedbackAnalysisTab() {
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [promptEnhancement, setPromptEnhancement] = useState<PromptEnhancement | null>(null)
  const [examples, setExamples] = useState<{ good: ExampleItem[], bad: ExampleItem[] }>({ good: [], bad: [] })
  const [backupModalOpen, setBackupModalOpen] = useState(false)

  useEffect(() => {
    loadAllData()
  }, [])

  const loadAllData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // 각 API 호출을 개별적으로 처리하여 일부가 실패해도 다른 데이터는 표시
      const promises = [
        feedbackApi.getStats().catch(err => {
          console.error('Failed to load stats:', err)
          return null
        }),
        feedbackApi.getPromptEnhancement().catch(err => {
          console.error('Failed to load prompt enhancement:', err)
          return null
        }),
        feedbackApi.getExamples('good', 5).catch(err => {
          console.error('Failed to load good examples:', err)
          return { examples: [] }
        }),
        feedbackApi.getExamples('bad', 5).catch(err => {
          console.error('Failed to load bad examples:', err)
          return { examples: [] }
        })
      ]

      const [statsData, enhancementData, goodExamples, badExamples] = await Promise.all(promises)

      if (statsData) {
        setStats(statsData)
      } else {
        // 기본 통계 데이터 설정
        setStats({
          total_feedback: 0,
          category_distribution: { good: 0, bad: 0, neutral: 0 },
          average_scores: { overall: 0, usefulness: 0, accuracy: 0, completeness: 0 }
        })
      }

      
      if (enhancementData) {
        setPromptEnhancement(enhancementData)
      }
      
      setExamples({
        good: goodExamples?.examples || [],
        bad: badExamples?.examples || []
      })

    } catch (error) {
      console.error('Failed to load feedback data:', error)
      setError('데이터를 불러오는 중 오류가 발생했습니다.')
      
      // 에러가 발생해도 기본 UI를 표시하기 위한 기본 데이터 설정
      setStats({
        total_feedback: 0,
        category_distribution: { good: 0, bad: 0, neutral: 0 },
        average_scores: { overall: 0, usefulness: 0, accuracy: 0, completeness: 0 }
      })
    } finally {
      setLoading(false)
    }
  }

  const handleExportData = async () => {
    try {
      await feedbackApi.exportData()
      alert('피드백 데이터가 성공적으로 내보내졌습니다.')
    } catch (error) {
      console.error('Failed to export data:', error)
      alert('데이터 내보내기 중 오류가 발생했습니다.')
    }
  }

  const handleResetFeedback = async (type: 'all' | 'good' | 'bad' | 'neutral') => {
    const typeLabels = {
      all: '모든',
      good: '긍정',
      bad: '부정', 
      neutral: '중립'
    }
    
    const confirmMessage = `${typeLabels[type]} 피드백을 삭제하시겠습니까? (백업이 자동으로 생성됩니다)`
    
    if (!confirm(confirmMessage)) return

    try {
      if (type === 'all') {
        await feedbackApi.resetAll(true)
      } else {
        await feedbackApi.resetByCategory(type as 'good' | 'bad' | 'neutral', true)
      }
      
      alert('피드백이 성공적으로 삭제되었습니다.')
      loadAllData()
    } catch (error) {
      console.error('Failed to reset feedback:', error)
      alert('피드백 삭제 중 오류가 발생했습니다.')
    }
  }

  const handleBackupManagement = () => {
    setBackupModalOpen(true)
  }

  const handleGenerateReport = async () => {
    try {
      const response = await feedbackApi.generateSummaryReport()
      
      // JSON 파일로 다운로드
      const blob = new Blob([JSON.stringify(response.report_data, null, 2)], {
        type: 'application/json'
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = response.filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      alert('요약 보고서가 성공적으로 생성되었습니다.')
    } catch (error) {
      console.error('Failed to generate summary report:', error)
      alert('요약 보고서 생성 중 오류가 발생했습니다.')
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        📊 피드백 분석 대시보드
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!stats || stats.total_feedback === 0 ? (
        <Alert severity="info">
          아직 수집된 피드백이 없습니다. 시나리오를 생성하고 평가를 남겨주세요!
        </Alert>
      ) : (
        <>
          {/* 전체 통계 */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="h4" color="primary">
                  {stats.total_feedback}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  총 피드백 수
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="h4" color="success.main">
                  {stats.category_distribution.good || 0}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  좋은 예시
                </Typography>
                <Typography variant="caption" display="block">
                  ({((stats.category_distribution.good || 0) / Math.max(stats.total_feedback, 1) * 100).toFixed(1)}%)
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="h4" color="error.main">
                  {stats.category_distribution.bad || 0}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  개선 필요
                </Typography>
                <Typography variant="caption" display="block">
                  ({((stats.category_distribution.bad || 0) / Math.max(stats.total_feedback, 1) * 100).toFixed(1)}%)
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="h4" color="primary">
                  {(stats.average_scores.overall ?? 0).toFixed(1)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  평균 만족도 (/5.0)
                </Typography>
              </Paper>
            </Grid>
          </Grid>

          {/* 상세 점수 분석 */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                📈 상세 점수 분석
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(stats.average_scores).map(([key, score]) => {
                  const labels: { [key: string]: string } = {
                    overall: '전체 만족도',
                    usefulness: '유용성',
                    accuracy: '정확성',
                    completeness: '완성도'
                  }
                  
                  return (
                    <Grid item xs={12} sm={6} md={3} key={key}>
                      <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                        <Typography variant="h6">
                          {(typeof score === 'number' ? score : 0).toFixed(1)}/5.0
                        </Typography>
                        <Typography variant="caption">
                          {labels[key] || key}
                        </Typography>
                      </Box>
                    </Grid>
                  )
                })}
              </Grid>
            </CardContent>
          </Card>

          {/* 프롬프트 개선 현황 */}
          {promptEnhancement && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  🔧 프롬프트 개선 현황
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                      <Typography variant="subtitle1">
                        {promptEnhancement.is_active ? '활성화' : '대기 중'}
                      </Typography>
                      <Typography variant="caption">
                        개선 적용 상태
                      </Typography>
                      <Typography variant="caption" display="block">
                        ({promptEnhancement?.enhancement_summary?.feedback_count ?? 0}/3 피드백)
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                      <Typography variant="subtitle1">
                        {promptEnhancement.enhancement_summary?.improvement_areas?.length || 0}개
                      </Typography>
                      <Typography variant="caption">
                        개선 필요 영역
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                      <Typography variant="subtitle1">
                        {((promptEnhancement.enhancement_summary?.good_examples_available || 0) + 
                         (promptEnhancement.enhancement_summary?.bad_examples_available || 0))}개
                      </Typography>
                      <Typography variant="caption">
                        사용 가능한 예시
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>

                {promptEnhancement?.is_active ? (
                  <Alert severity="success" sx={{ mt: 2 }}>
                    <Typography>
                      ✅ <strong>프롬프트 개선이 활성화되었습니다!</strong>
                    </Typography>
                    <Typography variant="body2">
                      충분한 피드백이 수집되어 AI 프롬프트 개선이 가능합니다.
                    </Typography>
                  </Alert>
                ) : (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    💡 {Math.max(0, 3 - (promptEnhancement?.enhancement_summary?.feedback_count ?? 0))}개의 추가 피드백이 필요합니다.
                    피드백이 충분히 수집되면 자동으로 프롬프트 개선이 활성화됩니다.
                  </Alert>
                )}
              </CardContent>
            </Card>
          )}

          {/* 예시 모음 */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TrendingUp color="success" />
                    좋은 예시 (최근 5개)
                  </Typography>
                  
                  {examples.good.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      좋은 예시가 없습니다.
                    </Typography>
                  ) : (
                    examples.good.map((example, index) => (
                      <Accordion key={index}>
                        <AccordionSummary expandIcon={<ExpandMore />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip label={`${example.overall_score}/5`} color="success" size="small" />
                            <Typography variant="body2">
                              {typeof example.timestamp === 'string' ? example.timestamp.slice(0, 10) : 'N/A'}
                            </Typography>
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="subtitle2">
                            시나리오 제목: {example.scenario_content?.test_scenario_name || 'N/A'}
                          </Typography>
                          {example.comments && typeof example.comments === 'string' && (
                            <Typography variant="body2" sx={{ mt: 1 }}>
                              의견: {example.comments}
                            </Typography>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    ))
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TrendingDown color="error" />
                    개선 필요 예시 (최근 5개)
                  </Typography>
                  
                  {examples.bad.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      개선 필요 예시가 없습니다.
                    </Typography>
                  ) : (
                    examples.bad.map((example, index) => (
                      <Accordion key={index}>
                        <AccordionSummary expandIcon={<ExpandMore />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip label={`${example.overall_score}/5`} color="error" size="small" />
                            <Typography variant="body2">
                              {typeof example.timestamp === 'string' ? example.timestamp.slice(0, 10) : 'N/A'}
                            </Typography>
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="subtitle2">
                            시나리오 제목: {example.scenario_content?.test_scenario_name || 'N/A'}
                          </Typography>
                          {example.comments && typeof example.comments === 'string' && (
                            <Typography variant="body2" sx={{ mt: 1 }}>
                              개선 의견: {example.comments}
                            </Typography>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    ))
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}

      {/* 데이터 관리 */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            💾 데이터 관리
          </Typography>
          
          {/* 안전한 작업 - 데이터 백업 및 관리 */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom sx={{ color: 'text.secondary' }}>
              데이터 백업 및 관리
            </Typography>
            <Grid container spacing={2} justifyContent="center">
              <Grid item xs={12} sm={4}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<Download />}
                  onClick={handleExportData}
                  sx={{ py: 1.5 }}
                >
                  📥 피드백 데이터 내보내기
                </Button>
              </Grid>
              
              <Grid item xs={12} sm={4}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<FolderOpen />}
                  onClick={handleBackupManagement}
                  sx={{ py: 1.5 }}
                >
                  📋 백업 파일 관리
                </Button>
              </Grid>
              
              <Grid item xs={12} sm={4}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<Assessment />}
                  onClick={handleGenerateReport}
                  sx={{ py: 1.5 }}
                >
                  📊 요약 보고서
                </Button>
              </Grid>
            </Grid>
          </Box>
          
          {/* 위험한 작업 - 데이터 삭제 */}
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 2, 
              backgroundColor: 'error.light', 
              borderColor: 'error.main',
              borderWidth: 1
            }}
          >
            <Typography variant="subtitle2" gutterBottom sx={{ color: 'error.dark', fontWeight: 'bold' }}>
              ⚠️ 데이터 삭제 (주의 필요)
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Button
                  fullWidth
                  variant="outlined"
                  color="error"
                  startIcon={<Delete />}
                  onClick={() => handleResetFeedback('all')}
                  sx={{ backgroundColor: 'white', '&:hover': { backgroundColor: 'error.light' } }}
                >
                  전체 피드백 삭제
                </Button>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Button
                  fullWidth
                  variant="outlined"
                  color="success"
                  startIcon={<Delete />}
                  onClick={() => handleResetFeedback('good')}
                  sx={{ backgroundColor: 'white', '&:hover': { backgroundColor: 'success.light' } }}
                >
                  긍정 피드백 삭제
                </Button>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Button
                  fullWidth
                  variant="outlined"
                  color="warning"
                  startIcon={<Delete />}
                  onClick={() => handleResetFeedback('bad')}
                  sx={{ backgroundColor: 'white', '&:hover': { backgroundColor: 'warning.light' } }}
                >
                  부정 피드백 삭제
                </Button>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Button
                  fullWidth
                  variant="outlined"
                  color="info"
                  startIcon={<Delete />}
                  onClick={() => handleResetFeedback('neutral')}
                  sx={{ backgroundColor: 'white', '&:hover': { backgroundColor: 'info.light' } }}
                >
                  중립 피드백 삭제
                </Button>
              </Grid>
            </Grid>
          </Paper>

          <Alert severity="warning" sx={{ mt: 2 }}>
            ⚠️ 초기화 작업은 되돌릴 수 없습니다. 초기화 전 자동으로 백업이 생성됩니다.
            백업 파일은 'backups/' 폴더에 저장됩니다.
          </Alert>
        </CardContent>
      </Card>

      {/* 백업 파일 관리 모달 */}
      <BackupFileManagementModal 
        open={backupModalOpen} 
        onClose={() => setBackupModalOpen(false)} 
      />
    </Box>
  )
}