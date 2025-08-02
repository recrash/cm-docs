import React, { useState, useEffect } from 'react'
import {
  Box,
  TextField,
  Button,
  FormControlLabel,
  Checkbox,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Chip,
  Paper
} from '@mui/material'
import { ExpandMore, Rocket, Psychology, Speed } from '@mui/icons-material'
import { scenarioApi, ragApi, filesApi } from '../services/api'
import { ScenarioWebSocket } from '../utils/websocket'
import ScenarioResultViewer from './ScenarioResultViewer'
import FeedbackModal from './FeedbackModal'
import RAGSystemPanel from './RAGSystemPanel'
import { type ScenarioResponse, type GenerationProgress, type RAGStatus, GenerationStatus } from '../types'

export default function ScenarioGenerationTab() {
  const [repoPath, setRepoPath] = useState('')
  const [performanceMode, setPerformanceMode] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const [result, setResult] = useState<ScenarioResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [ragStatus, setRagStatus] = useState<RAGStatus | null>(null)
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false)
  const [feedbackType, setFeedbackType] = useState<'like' | 'dislike'>('like')
  const [config, setConfig] = useState<any>(null)

  // WebSocket 인스턴스
  const [websocket, setWebsocket] = useState<ScenarioWebSocket | null>(null)

  useEffect(() => {
    // 컴포넌트 마운트 시 설정과 RAG 상태 로드
    loadConfig()
    loadRagStatus()
  }, [])

  useEffect(() => {
    // 컴포넌트 언마운트 시 WebSocket 정리
    return () => {
      if (websocket) {
        websocket.disconnect()
      }
    }
  }, [websocket])

  const loadConfig = async () => {
    try {
      const configData = await scenarioApi.getConfig()
      setConfig(configData)
      if (configData.repo_path) {
        setRepoPath(configData.repo_path)
      }
    } catch (error) {
      console.error('Failed to load config:', error)
    }
  }

  const loadRagStatus = async () => {
    try {
      const status = await ragApi.getStatus()
      setRagStatus(status)
    } catch (error) {
      console.error('Failed to load RAG status:', error)
    }
  }

  const validateRepoPath = async (path: string) => {
    if (!path.trim()) return false
    
    try {
      const validation = await filesApi.validateRepoPath(path)
      return validation.valid
    } catch (error) {
      return false
    }
  }

  const handleGenerate = async () => {
    if (!repoPath.trim()) {
      setError('Git 저장소 경로를 입력해주세요.')
      return
    }

    const isValid = await validateRepoPath(repoPath)
    if (!isValid) {
      setError('유효한 Git 저장소 경로를 입력해주세요.')
      return
    }

    setError(null)
    setResult(null)
    setIsGenerating(true)
    setProgress({ status: GenerationStatus.STARTED, message: '시나리오 생성을 시작합니다...', progress: 0 })

    // WebSocket 연결
    const wsUrl = scenarioApi.getWebSocketUrl()
    const ws = new ScenarioWebSocket(
      wsUrl,
      (progressData) => {
        setProgress(progressData)
      },
      (errorMessage) => {
        setError(errorMessage)
        setIsGenerating(false)
        setProgress(null)
      },
      (resultData) => {
        setResult(resultData)
        setIsGenerating(false)
        setProgress(null)
      }
    )

    setWebsocket(ws)
    ws.connect({
      repo_path: repoPath,
      use_performance_mode: performanceMode
    })
  }


  const handleFeedback = (type: 'like' | 'dislike') => {
    setFeedbackType(type)
    setFeedbackModalOpen(true)
  }

  const getProgressColor = () => {
    if (!progress) return 'primary'
    if (progress.status === 'error') return 'error'
    if (progress.status === 'completed') return 'success'
    return 'primary'
  }

  return (
    <Box>
      {/* RAG 시스템 정보 */}
      <RAGSystemPanel ragStatus={ragStatus} onStatusUpdate={loadRagStatus} />

      {/* 입력 폼 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            시나리오 생성 설정
          </Typography>
          
          <TextField
            fullWidth
            label="Git 저장소 경로"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="/path/to/your/git/repository"
            disabled={isGenerating}
            sx={{ mb: 2 }}
            helperText="분석할 Git 저장소의 로컬 경로를 입력하세요"
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={performanceMode}
                onChange={(e) => setPerformanceMode(e.target.checked)}
                disabled={isGenerating}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Speed fontSize="small" />
                성능 최적화 모드
                <Chip 
                  label="권장" 
                  size="small" 
                  color="primary" 
                  variant="outlined" 
                />
              </Box>
            }
            sx={{ mb: 2 }}
          />
          
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
            프롬프트 크기를 제한하여 LLM 응답 속도를 향상시킵니다.
          </Typography>

          <Button
            variant="contained"
            size="large"
            onClick={handleGenerate}
            disabled={isGenerating}
            startIcon={<Rocket />}
            fullWidth
          >
            {isGenerating ? '생성 중...' : '테스트 시나리오 생성하기'}
          </Button>
        </CardContent>
      </Card>

      {/* 진행 상황 표시 */}
      {progress && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              생성 진행 상황
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {progress.message}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={progress.progress}
              color={getProgressColor()}
              sx={{ mb: 1 }}
            />
            <Typography variant="caption" color="text.secondary">
              {progress.progress.toFixed(0)}% 완료
            </Typography>
            
            {progress.details && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  {progress.details.llm_response_time && 
                    `⏱️ LLM 응답 시간: ${progress.details.llm_response_time.toFixed(1)}초`}
                  {progress.details.prompt_size && 
                    ` • 📏 프롬프트 크기: ${progress.details.prompt_size.toLocaleString()}자`}
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* 오류 표시 */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* 결과 표시 */}
      {result && (
        <Box>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6" color="success.main">
                  ✅ 테스트 시나리오 생성이 완료되었습니다!
                </Typography>
              </Box>

              {result.metadata && (
                <Box sx={{ mb: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="caption" color="text.secondary">
                          LLM 응답 시간
                        </Typography>
                        <Typography variant="h6">
                          {result.metadata.llm_response_time.toFixed(1)}초
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="caption" color="text.secondary">
                          프롬프트 크기
                        </Typography>
                        <Typography variant="h6">
                          {result.metadata.prompt_size.toLocaleString()}자
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="caption" color="text.secondary">
                          RAG 청크 수
                        </Typography>
                        <Typography variant="h6">
                          {result.metadata.added_chunks}개
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </CardContent>
          </Card>

          <ScenarioResultViewer result={result} onFeedback={handleFeedback} />
        </Box>
      )}

      {/* 피드백 모달 */}
      {result && (
        <FeedbackModal
          open={feedbackModalOpen}
          onClose={() => setFeedbackModalOpen(false)}
          feedbackType={feedbackType}
          result={result}
          repoPath={repoPath}
        />
      )}
    </Box>
  )
}