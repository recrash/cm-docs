import { useState, useEffect } from 'react'
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
  Grid,
  Chip,
  Paper
} from '@mui/material'
import { Rocket, Psychology, Speed } from '@mui/icons-material'
import { ragApi, filesApi } from '../services/api'
import { V2ProgressWebSocket, generateClientId, type V2ProgressMessage, V2GenerationStatus } from '../services/v2WebSocket'
import ScenarioResultViewer from './ScenarioResultViewer'
import FeedbackModal from './FeedbackModal'
import RAGSystemPanel from './RAGSystemPanel'
import { type ScenarioResponse, type RAGStatus, type V2ResultData } from '../types'

export default function ScenarioGenerationTab() {
  const [repoPath, setRepoPath] = useState('')
  const [performanceMode, setPerformanceMode] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [result, setResult] = useState<ScenarioResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [ragStatus, setRagStatus] = useState<RAGStatus | null>(null)
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false)
  const [feedbackType, setFeedbackType] = useState<'like' | 'dislike'>('like')

  // v2 CLI 연동 관련 state
  const [v2Progress, setV2Progress] = useState<V2ProgressMessage | null>(null)
  const [v2WebSocket, setV2WebSocket] = useState<V2ProgressWebSocket | null>(null)
  const [isWaitingForCLI, setIsWaitingForCLI] = useState(false)

  useEffect(() => {
    // 컴포넌트 마운트 시 RAG 상태 로드
    loadRagStatus()
  }, [])

  useEffect(() => {
    // 컴포넌트 언마운트 시 WebSocket 정리
    return () => {
      if (v2WebSocket) {
        v2WebSocket.disconnect()
      }
    }
  }, [v2WebSocket])


  const loadRagStatus = async () => {
    try {
      const status = await ragApi.getStatus()
      setRagStatus(status)
      setError(null) // Clear any previous errors
    } catch (error) {
      console.error('Failed to load RAG status:', error)
      const errorMessage = error instanceof Error ? error.message : 'RAG 상태를 불러오지 못했습니다.'
      setError(errorMessage)
      // Set a fallback status to prevent infinite loading
      setRagStatus({
        status: 'error',
        message: errorMessage,
        document_count: 0,
        embedding_model: 'Unknown',
        chunk_size: 0
      })
    }
  }

  const validateRepoPath = async (path: string) => {
    if (!path.trim()) return false
    
    // 클라이언트사이드 기본 검증
    const isValidFormat = isValidPathFormat(path)
    if (!isValidFormat) return false
    
    // 로컬 환경에서만 서버 검증 수행
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      try {
        const validation = await filesApi.validateRepoPath(path)
        return validation.valid
      } catch (error) {
        console.warn('서버 검증 실패, 클라이언트 검증 사용:', error)
      }
    }
    
    // 원격 환경이거나 서버 검증 실패시 클라이언트 검증 결과 사용
    return true
  }

  // 클라이언트사이드 경로 형식 검증
  const isValidPathFormat = (path: string): boolean => {
    // 기본 보안 검증
    if (path.includes('..') || path.includes('<') || path.includes('>')) {
      return false
    }
    
    // 빈 경로 제외
    if (path.trim().length === 0) {
      return false
    }
    
    // 기본적인 경로 형식 검증 (Windows, Unix 경로 모두 지원)
    // Windows: C:\path\to\repo or D:/path/to/repo
    // Unix: /path/to/repo or ~/path/to/repo or ./path/to/repo
    const pathPattern = /^([a-zA-Z]:[/\\]|[/\\~.]|\.\.?[/\\])?[\w\s\-_./\\]+$/
    return pathPattern.test(path)
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

    // v2 CLI 연동 모드로만 동작
    await handleV2Generate()
  }

  const handleV2Generate = async () => {
    try {
      // 상태 초기화
      setError(null)
      setResult(null)
      setV2Progress(null)
      setIsGenerating(true)
      setIsWaitingForCLI(true)

      // 고유한 클라이언트 ID 생성
      const clientId = generateClientId()

      console.log('🚀 v2 모드로 시나리오 생성 시작:', { clientId, repoPath })

      // v2 WebSocket 연결 준비
      const v2WS = new V2ProgressWebSocket(clientId, {
        onProgress: (progress) => {
          console.log('📊 v2 진행 상황:', progress)
          setV2Progress(progress)
          setIsWaitingForCLI(false) // CLI가 응답하면 대기 상태 해제
        },
        onError: (errorMessage) => {
          console.error('❌ v2 오류:', errorMessage)
          setError(`v2 시나리오 생성 오류: ${errorMessage}`)
          setIsGenerating(false)
          setIsWaitingForCLI(false)
          setV2Progress(null)
        },
        onComplete: (resultData: V2ResultData) => {
          console.log('🎉 v2 시나리오 생성 완료!', resultData)
          
          // v1 형식으로 변환하여 기존 컴포넌트와 호환
          const convertedResult: ScenarioResponse = {
            scenario_description: resultData.description || '',
            test_scenario_name: resultData.test_scenario_name || (resultData.filename ? resultData.filename.replace('.xlsx', '') : ''),
            test_cases: resultData.test_cases || [], // v2에서 실제 테스트 케이스 데이터 사용
            metadata: {
              llm_response_time: resultData.llm_response_time || 0,
              prompt_size: resultData.prompt_size || 0,
              added_chunks: resultData.added_chunks || 0,
              excel_filename: resultData.filename || ''
            }
          }

          setResult(convertedResult)
          setIsGenerating(false)
          setIsWaitingForCLI(false)
          setV2Progress(null)
        }
      })

      setV2WebSocket(v2WS)
      v2WS.connect()

      // Custom URL Protocol로 CLI 실행
      const customUrl = `testscenariomaker://generate?clientId=${clientId}&repoPath=${encodeURIComponent(repoPath)}&performanceMode=${performanceMode}`
      
      console.log('🔗 CLI 실행 URL:', customUrl)
      
      // CLI 실행 시도
      try {
        window.location.href = customUrl
        console.log('✅ CLI 실행 URL 호출 완료')
      } catch (urlError) {
        console.error('❌ CLI URL 호출 실패:', urlError)
        throw new Error('CLI를 실행할 수 없습니다. CLI가 설치되어 있는지 확인해주세요.')
      }

    } catch (error) {
      console.error('❌ v2 생성 처리 오류:', error)
      setError(error instanceof Error ? error.message : 'v2 시나리오 생성 중 오류가 발생했습니다.')
      setIsGenerating(false)
      setIsWaitingForCLI(false)
    }
  }



  const handleFeedback = (type: 'like' | 'dislike') => {
    setFeedbackType(type)
    setFeedbackModalOpen(true)
  }

  const getProgressColor = () => {
    if (v2Progress) {
      if (v2Progress.status === V2GenerationStatus.ERROR) return 'error'
      if (v2Progress.status === V2GenerationStatus.COMPLETED) return 'success'
      return 'primary'
    }
    return 'primary'
  }

  return (
    <Box>
      {/* RAG 시스템 정보 */}
      <RAGSystemPanel ragStatus={ragStatus} onStatusUpdate={loadRagStatus} />

      {/* 입력 폼 */}
      <Card 
        sx={{ 
          mb: 4, 
          background: 'linear-gradient(135deg, #ffffff 0%, #f8faff 100%)',
          border: '2px solid rgba(33, 150, 243, 0.1)',
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '4px',
            background: 'linear-gradient(90deg, #2196f3 0%, #1976d2 100%)'
          }
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <Rocket sx={{ mr: 2, color: 'primary.main', fontSize: 28 }} />
            <Typography variant="h5" fontWeight={700} color="primary.main">
              시나리오 생성 설정
            </Typography>
          </Box>
          
          <TextField
            fullWidth
            label="Git 저장소 경로"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="/path/to/your/git/repository"
            disabled={isGenerating}
            sx={{ 
              mb: 3,
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 1)'
                }
              }
            }}
            helperText="분석할 Git 저장소의 로컬 경로를 입력하세요"
          />


          <Box 
            sx={{ 
              p: 3, 
              backgroundColor: 'rgba(33, 150, 243, 0.04)',
              borderRadius: 3,
              border: '1px solid rgba(33, 150, 243, 0.1)',
              mb: 3
            }}
          >
            <FormControlLabel
              control={
                <Checkbox
                  checked={performanceMode}
                  onChange={(e) => setPerformanceMode(e.target.checked)}
                  disabled={isGenerating}
                  sx={{
                    '& .MuiSvgIcon-root': {
                      fontSize: 24
                    }
                  }}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 1 }}>
                  <Speed fontSize="small" color="primary" />
                  <Typography variant="body1" fontWeight={500}>
                    성능 최적화 모드
                  </Typography>
                  <Chip 
                    label="권장" 
                    size="small" 
                    color="primary" 
                    sx={{ 
                      fontWeight: 600,
                      background: 'linear-gradient(45deg, #2196f3 30%, #1976d2 90%)'
                    }}
                  />
                </Box>
              }
              sx={{ mb: 1 }}
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 5 }}>
              프롬프트 크기를 제한하여 LLM 응답 속도를 향상시킵니다.
            </Typography>
          </Box>
          
          <Button
            variant="contained"
            size="large"
            onClick={handleGenerate}
            disabled={isGenerating}
            startIcon={<Rocket />}
            fullWidth
            sx={{
              py: 2,
              fontSize: '1.1rem',
              fontWeight: 700,
              background: isGenerating 
                ? 'linear-gradient(45deg, #bdbdbd 30%, #9e9e9e 90%)' 
                : 'linear-gradient(45deg, #2196f3 30%, #1976d2 90%)',
              boxShadow: '0 6px 20px rgba(33, 150, 243, 0.3)',
              '&:hover': {
                background: 'linear-gradient(45deg, #1976d2 30%, #1565c0 90%)',
                boxShadow: '0 8px 25px rgba(33, 150, 243, 0.4)',
                transform: 'translateY(-2px)'
              },
              '&:disabled': {
                background: 'linear-gradient(45deg, #bdbdbd 30%, #9e9e9e 90%)',
                color: 'white'
              }
            }}
          >
            {isGenerating ? '생성 중...' : '테스트 시나리오 생성하기'}
          </Button>
        </CardContent>
      </Card>

      {/* CLI 대기 상태 표시 */}
      {isWaitingForCLI && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body1" fontWeight={500}>
            🔗 CLI 애플리케이션을 실행하고 있습니다...
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            CLI가 설치되어 있지 않다면 먼저 설치해주세요. 
            잠시 후 진행 상황이 업데이트됩니다.
          </Typography>
        </Alert>
      )}

      {/* 진행 상황 표시 */}
      {v2Progress && (
        <Card 
          sx={{ 
            mb: 4,
            background: 'linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%)',
            border: '2px solid rgba(33, 150, 243, 0.2)',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Box 
                sx={{ 
                  width: 48, 
                  height: 48, 
                  borderRadius: '50%', 
                  background: 'linear-gradient(45deg, #2196f3 30%, #1976d2 90%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mr: 2,
                  boxShadow: '0 4px 12px rgba(33, 150, 243, 0.3)'
                }}
              >
                <Psychology sx={{ color: 'white', fontSize: 24 }} />
              </Box>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h5" fontWeight={700} color="primary.main">
                  생성 진행 상황
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
                  {v2Progress.message}
                </Typography>
              </Box>
              <Chip
                label={`${v2Progress.progress.toFixed(0)}%`}
                color="primary"
                sx={{
                  fontSize: '1rem',
                  fontWeight: 700,
                  height: 40,
                  background: 'linear-gradient(45deg, #2196f3 30%, #1976d2 90%)'
                }}
              />
            </Box>
            
            <Box sx={{ mb: 2 }}>
              <LinearProgress
                variant="determinate"
                value={v2Progress.progress}
                color={getProgressColor()}
                sx={{ 
                  height: 12,
                  borderRadius: 6,
                  backgroundColor: 'rgba(33, 150, 243, 0.1)',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 6,
                    background: 'linear-gradient(90deg, #2196f3 0%, #1976d2 100%)'
                  }
                }}
              />
            </Box>
            
            {v2Progress.details && (
              <Box 
                sx={{ 
                  mt: 3,
                  p: 2,
                  backgroundColor: 'rgba(255, 255, 255, 0.8)',
                  borderRadius: 2,
                  border: '1px solid rgba(33, 150, 243, 0.1)'
                }}
              >
                <Grid container spacing={2}>
                  {v2Progress.details && typeof v2Progress.details === 'object' && 'llm_response_time' in v2Progress.details && (
                    <Grid item xs={12} sm={6}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Typography variant="body2" color="text.secondary">
                          ⏱️ LLM 응답 시간: 
                        </Typography>
                        <Typography variant="body2" fontWeight={600} sx={{ ml: 1 }}>
                          {typeof v2Progress.details.llm_response_time === 'number' ? v2Progress.details.llm_response_time.toFixed(1) : '0'}초
                        </Typography>
                      </Box>
                    </Grid>
                  )}
                  {Boolean(v2Progress.details && typeof v2Progress.details === 'object' && 'prompt_size' in v2Progress.details && v2Progress.details.prompt_size) && (
                    <Grid item xs={12} sm={6}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Typography variant="body2" color="text.secondary">
                          📏 프롬프트 크기: 
                        </Typography>
                        <Typography variant="body2" fontWeight={600} sx={{ ml: 1 }}>
                          {typeof v2Progress.details.prompt_size === 'number' ? v2Progress.details.prompt_size.toLocaleString() : '0'}자
                        </Typography>
                      </Box>
                    </Grid>
                  )}
                </Grid>
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
          <Card 
            sx={{ 
              mb: 4,
              background: 'linear-gradient(135deg, #e8f5e8 0%, #ffffff 100%)',
              border: '2px solid rgba(76, 175, 80, 0.2)',
              position: 'relative',
              overflow: 'hidden'
            }}
          >
            <CardContent sx={{ p: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
                <Box 
                  sx={{ 
                    width: 56, 
                    height: 56, 
                    borderRadius: '50%', 
                    background: 'linear-gradient(45deg, #4caf50 30%, #388e3c 90%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    mr: 3,
                    boxShadow: '0 6px 16px rgba(76, 175, 80, 0.3)'
                  }}
                >
                  <Typography sx={{ fontSize: '2rem' }}>✅</Typography>
                </Box>
                <Typography variant="h4" fontWeight={700} color="success.main">
                  테스트 시나리오 생성 완료!
                </Typography>
              </Box>

              {result.metadata && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="h6" gutterBottom sx={{ mb: 3, color: 'text.secondary' }}>
                    📊 생성 통계
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={4}>
                      <Paper 
                        elevation={0}
                        sx={{ 
                          p: 3, 
                          textAlign: 'center',
                          background: 'linear-gradient(135deg, #fff3e0 0%, #ffffff 100%)',
                          border: '1px solid rgba(255, 152, 0, 0.2)',
                          borderRadius: 3
                        }}
                      >
                        <Typography variant="h4" fontWeight={700} color="warning.main" sx={{ mb: 1 }}>
                          {result.metadata.llm_response_time.toFixed(1)}
                        </Typography>
                        <Typography variant="subtitle2" color="text.secondary">
                          ⏱️ LLM 응답 시간 (초)
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Paper 
                        elevation={0}
                        sx={{ 
                          p: 3, 
                          textAlign: 'center',
                          background: 'linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%)',
                          border: '1px solid rgba(33, 150, 243, 0.2)',
                          borderRadius: 3
                        }}
                      >
                        <Typography variant="h4" fontWeight={700} color="primary.main" sx={{ mb: 1 }}>
                          {result.metadata.prompt_size.toLocaleString()}
                        </Typography>
                        <Typography variant="subtitle2" color="text.secondary">
                          📏 프롬프트 크기 (문자)
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Paper 
                        elevation={0}
                        sx={{ 
                          p: 3, 
                          textAlign: 'center',
                          background: 'linear-gradient(135deg, #f3e5f5 0%, #ffffff 100%)',
                          border: '1px solid rgba(156, 39, 176, 0.2)',
                          borderRadius: 3
                        }}
                      >
                        <Typography variant="h4" fontWeight={700} color="secondary.main" sx={{ mb: 1 }}>
                          {result.metadata.added_chunks}
                        </Typography>
                        <Typography variant="subtitle2" color="text.secondary">
                          🧩 RAG 청크 수 (개)
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