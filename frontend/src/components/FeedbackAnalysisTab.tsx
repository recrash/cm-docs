import React, { useState, useEffect } from 'react'
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
  Analytics,
  TrendingUp,
  TrendingDown
} from '@mui/icons-material'
import { feedbackApi } from '../services/api'
import type { FeedbackStats } from '../types'

export default function FeedbackAnalysisTab() {
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [insights, setInsights] = useState<any>(null)
  const [promptEnhancement, setPromptEnhancement] = useState<any>(null)
  const [examples, setExamples] = useState<{ good: any[], bad: any[] }>({ good: [], bad: [] })

  useEffect(() => {
    loadAllData()
  }, [])

  const loadAllData = async () => {
    try {
      setLoading(true)
      
      const [statsData, insightsData, enhancementData, goodExamples, badExamples] = await Promise.all([
        feedbackApi.getStats(),
        feedbackApi.getInsights(),
        feedbackApi.getPromptEnhancement(),
        feedbackApi.getExamples('good', 5),
        feedbackApi.getExamples('bad', 5)
      ])

      setStats(statsData)
      setInsights(insightsData)
      setPromptEnhancement(enhancementData)
      setExamples({
        good: goodExamples.examples || [],
        bad: badExamples.examples || []
      })
    } catch (error) {
      console.error('Failed to load feedback data:', error)
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

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!stats || stats.total_feedback === 0) {
    return (
      <Alert severity="info">
        아직 수집된 피드백이 없습니다. 시나리오를 생성하고 평가를 남겨주세요!
      </Alert>
    )
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        📊 피드백 분석 대시보드
      </Typography>

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
              ({((stats.category_distribution.good || 0) / stats.total_feedback * 100).toFixed(1)}%)
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
              ({((stats.category_distribution.bad || 0) / stats.total_feedback * 100).toFixed(1)}%)
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="primary">
              {stats.average_scores.overall?.toFixed(1) || '0.0'}
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
                      {(score as number).toFixed(1)}/5.0
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
                    ({promptEnhancement.enhancement_summary.feedback_count}/3 피드백)
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={4}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle1">
                    {promptEnhancement.enhancement_summary.improvement_areas?.length || 0}개
                  </Typography>
                  <Typography variant="caption">
                    개선 필요 영역
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={4}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle1">
                    {(promptEnhancement.enhancement_summary.good_examples_available || 0) + 
                     (promptEnhancement.enhancement_summary.bad_examples_available || 0)}개
                  </Typography>
                  <Typography variant="caption">
                    사용 가능한 예시
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {promptEnhancement.is_active ? (
              <Alert severity="success" sx={{ mt: 2 }}>
                ✅ 피드백 기반 프롬프트 개선이 활성화되어 있습니다.
              </Alert>
            ) : (
              <Alert severity="info" sx={{ mt: 2 }}>
                💡 {3 - promptEnhancement.enhancement_summary.feedback_count}개의 추가 피드백이 필요합니다. 
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
                          {example.timestamp?.slice(0, 10)}
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="subtitle2">
                        시나리오 제목: {example.scenario_content?.test_scenario_name || 'N/A'}
                      </Typography>
                      {example.comments && (
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
                          {example.timestamp?.slice(0, 10)}
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="subtitle2">
                        시나리오 제목: {example.scenario_content?.test_scenario_name || 'N/A'}
                      </Typography>
                      {example.comments && (
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

      {/* 데이터 관리 */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            💾 데이터 관리
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<Download />}
                onClick={handleExportData}
              >
                피드백 데이터 내보내기
              </Button>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Button
                fullWidth
                variant="outlined"
                color="error"
                startIcon={<Delete />}
                onClick={() => handleResetFeedback('all')}
              >
                전체 피드백 삭제
              </Button>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Button
                fullWidth
                variant="outlined"
                color="success"
                startIcon={<Delete />}
                onClick={() => handleResetFeedback('good')}
              >
                긍정 피드백 삭제
              </Button>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Button
                fullWidth
                variant="outlined"
                color="warning"
                startIcon={<Delete />}
                onClick={() => handleResetFeedback('bad')}
              >
                부정 피드백 삭제
              </Button>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Button
                fullWidth
                variant="outlined"
                color="info"
                startIcon={<Delete />}
                onClick={() => handleResetFeedback('neutral')}
              >
                중립 피드백 삭제
              </Button>
            </Grid>
          </Grid>

          <Alert severity="warning" sx={{ mt: 2 }}>
            ⚠️ 초기화 작업은 되돌릴 수 없습니다. 초기화 전 자동으로 백업이 생성됩니다.
            백업 파일은 'backups/' 폴더에 저장됩니다.
          </Alert>
        </CardContent>
      </Card>
    </Box>
  )
}