import React, { useState, useEffect, useRef } from 'react'
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
  Chip
} from '@mui/material'
import { 
  Rocket, 
  Psychology, 
  Speed, 
  CloudUpload,
  Article,
  Download,
  FolderOpen,
  CheckCircle,
  Error as ErrorIcon,
  HourglassEmpty,
  Description,
  ListAlt,
  Assignment
} from '@mui/icons-material'
import { ragApi, filesApi, autodocApi, v2Api } from '../services/api'
import { V2ProgressWebSocket, generateClientId, generateSessionId, type V2ProgressMessage, V2GenerationStatus } from '../services/v2WebSocket'
import { FullGenerationWebSocket } from '../services/fullGenerationWebSocket'
import ScenarioResultViewer from './ScenarioResultViewer'
import FeedbackModal from './FeedbackModal'
import RAGSystemPanel from './RAGSystemPanel'
import { 
  type ScenarioResponse, 
  type RAGStatus, 
  type V2ResultData,
  type WorkflowState,
  type FullGenerationProgressMessage,
  type FullGenerationResultData,
  FullGenerationStatus
} from '../types'

export default function ScenarioGenerationTab() {
  // 공통 state
  const [repoPath, setRepoPath] = useState('')
  const [performanceMode, setPerformanceMode] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [ragStatus, setRagStatus] = useState<RAGStatus | null>(null)
  
  // 기존 기능 state (테스트 시나리오만)
  const [isGenerating, setIsGenerating] = useState(false)
  const [result, setResult] = useState<ScenarioResponse | null>(null)
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false)
  const [feedbackType, setFeedbackType] = useState<'like' | 'dislike'>('like')
  const [v2Progress, setV2Progress] = useState<V2ProgressMessage | null>(null)
  const [v2WebSocket, setV2WebSocket] = useState<V2ProgressWebSocket | null>(null)
  const [isWaitingForCLI, setIsWaitingForCLI] = useState(false)
  
  // Phase 3 전용 state (전체 문서 생성)
  const [workflowState, setWorkflowState] = useState<WorkflowState>('idle')
  const [htmlFile, setHtmlFile] = useState<File | null>(null)
  const [, setFullGenSessionId] = useState<string>('')
  const [fullGenProgress, setFullGenProgress] = useState<FullGenerationProgressMessage | null>(null)
  const [fullGenResult, setFullGenResult] = useState<FullGenerationResultData | null>(null)
  const [fullGenWebSocket, setFullGenWebSocket] = useState<FullGenerationWebSocket | null>(null)
  const [cliTimeout, setCliTimeout] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
      if (fullGenWebSocket) {
        fullGenWebSocket.disconnect()
      }
      if (cliTimeout) {
        clearTimeout(cliTimeout)
      }
    }
  }, [v2WebSocket, fullGenWebSocket, cliTimeout])

  const loadRagStatus = async () => {
    try {
      const status = await ragApi.getStatus()
      setRagStatus(status)
      setError(null)
    } catch (error) {
      console.error('Failed to load RAG status:', error)
      const errorMessage = error instanceof Error ? error.message : 'RAG 상태를 불러오지 못했습니다.'
      setError(errorMessage)
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
    if (import.meta.env.DEV || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      try {
        const validation = await filesApi.validateRepoPath(path)
        return validation.valid
      } catch (error) {
        console.warn('서버 검증 실패, 클라이언트 검증 사용:', error)
      }
    }
    
    return true
  }

  const isValidPathFormat = (path: string): boolean => {
    if (path.includes('..') || path.includes('<') || path.includes('>')) {
      return false
    }
    if (path.trim().length === 0) {
      return false
    }
    const pathPattern = /^([a-zA-Z]:[/\\]|[/\\~.]|\.\.?[/\\])?[\w\s\-_./\\]+$/
    return pathPattern.test(path)
  }

  // 기존 기능: 테스트 시나리오만 생성
  const handleBasicGenerate = async () => {
    if (!repoPath.trim()) {
      setError('저장소 경로를 입력해주세요.')
      return
    }

    const isValid = await validateRepoPath(repoPath)
    if (!isValid) {
      setError('유효한 저장소 경로를 입력해주세요.')
      return
    }

    await handleV2Generate()
  }

  const handleV2Generate = async () => {
    try {
      setError(null)
      setResult(null)
      setV2Progress(null)
      setIsGenerating(true)
      setIsWaitingForCLI(true)

      const clientId = generateClientId()
      console.log('🚀 v2 모드로 시나리오 생성 시작:', { clientId, repoPath })

      const v2WS = new V2ProgressWebSocket(clientId, {
        onProgress: (progress) => {
          console.log('📊 v2 진행 상황:', progress)
          setV2Progress(progress)
          setIsWaitingForCLI(false)
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
          
          const convertedResult: ScenarioResponse = {
            scenario_description: resultData.description || '',
            test_scenario_name: resultData.test_scenario_name || (resultData.filename ? resultData.filename.replace('.xlsx', '') : ''),
            test_cases: resultData.test_cases || [],
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

      const customUrl = `testscenariomaker://generate?clientId=${clientId}&repoPath=${encodeURIComponent(repoPath)}&performanceMode=${performanceMode}`
      console.log('🔗 CLI 실행 URL:', customUrl)
      
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

  // Phase 3: 전체 문서 생성
  const handleFullGeneration = async () => {
    if (!repoPath.trim()) {
      setError('저장소 경로를 입력해주세요.')
      return
    }
    
    if (!htmlFile) {
      setError('HTML 파일을 선택해주세요.')
      return
    }

    const isValid = await validateRepoPath(repoPath)
    if (!isValid) {
      setError('유효한 저장소 경로를 입력해주세요.')
      return
    }

    try {
      // 상태 초기화
      setError(null)
      setFullGenResult(null)
      setFullGenProgress(null)
      setWorkflowState('parsing')
      
      // 1. sessionId 생성 (Full Generation용)
      const sessionId = generateSessionId()
      setFullGenSessionId(sessionId)
      console.log('📋 Full Generation 시작:', { sessionId, repoPath, htmlFile: htmlFile.name })
      
      // 2. 백엔드에 세션 사전 등록
      try {
        console.log('🔧 세션 초기화 중...')
        await v2Api.initFullGenerationSession(sessionId)
        console.log('✅ 세션 초기화 완료')
      } catch (sessionError) {
        console.error('❌ 세션 초기화 실패:', sessionError)
        setError('세션 초기화에 실패했습니다. 다시 시도해주세요.')
        setWorkflowState('error')
        return
      }
      
      // 3. WebSocket 연결
      const ws = new FullGenerationWebSocket(sessionId, {
        onProgress: (progress) => {
          console.log('📊 Full Generation 진행:', progress)
          setFullGenProgress(progress)
          
          // CLI가 응답하면 waiting_cli → processing
          if (workflowState === 'waiting_cli') {
            setWorkflowState('processing')
            // 타임아웃 클리어
            if (cliTimeout) {
              clearTimeout(cliTimeout)
              setCliTimeout(null)
            }
          }
        },
        onComplete: (result) => {
          console.log('✅ Full Generation 완료:', result)
          setFullGenResult(result)
          setWorkflowState('completed')
          setFullGenProgress(null)
          
          // 타임아웃 클리어
          if (cliTimeout) {
            clearTimeout(cliTimeout)
            setCliTimeout(null)
          }
        },
        onError: (errorMsg) => {
          console.error('❌ Full Generation 오류:', errorMsg)
          setError(`문서 생성 오류: ${errorMsg}`)
          setWorkflowState('error')
          setFullGenProgress(null)
          
          // 타임아웃 클리어
          if (cliTimeout) {
            clearTimeout(cliTimeout)
            setCliTimeout(null)
          }
        }
      })
      
      setFullGenWebSocket(ws)
      ws.connect()
      
      // 4. HTML 파일 파싱
      console.log('📄 HTML 파일 파싱 중...')
      const parseResult = await autodocApi.parseHtmlOnly(htmlFile)
      
      if (!parseResult.success || !parseResult.data) {
        throw new Error('HTML 파일 파싱 실패: 메타데이터를 추출할 수 없습니다.')
      }
      
      console.log('✅ HTML 파싱 완료:', parseResult)
      
      // 5. 메타데이터 Base64 인코딩
      const metadataJson = JSON.stringify(parseResult.data)
      const metadataBase64 = btoa(unescape(encodeURIComponent(metadataJson)))
      
      // 6. CLI 호출
      setWorkflowState('waiting_cli')
      const customUrl = `testscenariomaker://full-generate?sessionId=${sessionId}&repoPath=${encodeURIComponent(repoPath)}&metadata=${metadataBase64}`
      console.log('🔗 Full Generation CLI URL:', customUrl)
      
      window.location.href = customUrl
      
      // 7. 5분 타임아웃 설정 (LLM 처리 시간 고려)
      const timeout = setTimeout(() => {
        console.log('⏰ CLI 타임아웃')
        setError('CLI가 응답하지 않습니다. 프로그램이 설치되어 있는지 확인해주세요.')
        setWorkflowState('error')
        ws.disconnect()
      }, 300000)  // 30초 → 300초 (5분)로 증가
      
      setCliTimeout(timeout as unknown as number)
      
    } catch (error) {
      console.error('❌ Full Generation 오류:', error)
      setError(error instanceof Error ? error.message : '전체 문서 생성 중 오류가 발생했습니다.')
      setWorkflowState('error')
    }
  }

  // 파일 선택 핸들러
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      if (file.type !== 'text/html' && !file.name.endsWith('.html')) {
        setError('HTML 파일만 업로드 가능합니다.')
        return
      }
      setHtmlFile(file)
      setError(null)
    }
  }

  // 일괄 다운로드
  const handleDownloadAll = async () => {
    if (!fullGenResult?.download_urls) return
    
    try {
      await autodocApi.downloadAll(fullGenResult.download_urls)
    } catch (error) {
      console.error('다운로드 오류:', error)
      setError('파일 다운로드 중 오류가 발생했습니다.')
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
    if (fullGenProgress) {
      if (fullGenProgress.status === FullGenerationStatus.ERROR) return 'error'
      if (fullGenProgress.status === FullGenerationStatus.COMPLETED) return 'success'
      return 'primary'
    }
    return 'primary'
  }

  const getWorkflowStateIcon = () => {
    switch (workflowState) {
      case 'parsing': return <HourglassEmpty />
      case 'waiting_cli': return <HourglassEmpty />
      case 'processing': return <Psychology />
      case 'completed': return <CheckCircle />
      case 'error': return <ErrorIcon />
      default: return null
    }
  }

  const getWorkflowStateMessage = () => {
    switch (workflowState) {
      case 'parsing': return 'HTML 파일 파싱 중...'
      case 'waiting_cli': return 'CLI 실행을 기다리는 중...'
      case 'processing': return '문서 생성 중...'
      case 'completed': return '문서 생성 완료!'
      case 'error': return '오류가 발생했습니다.'
      default: return ''
    }
  }

  return (
    <Box>
      {/* RAG 시스템 정보 */}
      <RAGSystemPanel ragStatus={ragStatus} onStatusUpdate={loadRagStatus} />

      {/* 공통 입력 섹션 */}
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
            <FolderOpen sx={{ mr: 2, color: 'primary.main', fontSize: 28 }} />
            <Typography variant="h5" fontWeight={700} color="primary.main">
              VCS 저장소 경로 (필수)
            </Typography>
          </Box>
          
          <TextField
            fullWidth
            label="저장소 경로"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="/path/to/your/repository"
            disabled={isGenerating || workflowState !== 'idle'}
            sx={{ 
              mb: 3,
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 1)'
                }
              }
            }}
            helperText="분석할 저장소의 로컬 경로를 입력하세요 (Git 또는 SVN 저장소 지원)"
          />

          <Box 
            sx={{ 
              p: 3, 
              backgroundColor: 'rgba(33, 150, 243, 0.04)',
              borderRadius: 3,
              border: '1px solid rgba(33, 150, 243, 0.1)'
            }}
          >
            <FormControlLabel
              control={
                <Checkbox
                  checked={performanceMode}
                  onChange={(e) => setPerformanceMode(e.target.checked)}
                  disabled={isGenerating || workflowState !== 'idle'}
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
                    sx={{ fontWeight: 600 }}
                  />
                </Box>
              }
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 5 }}>
              프롬프트 크기를 제한하여 LLM 응답 속도를 향상시킵니다.
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* 작업 선택 섹션 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* 기존 기능: 테스트 시나리오만 */}
        <Grid item xs={12} md={6}>
          <Card 
            sx={{ 
              height: '100%',
              background: 'linear-gradient(135deg, #e8f5e9 0%, #ffffff 100%)',
              border: '2px solid rgba(76, 175, 80, 0.2)'
            }}
          >
            <CardContent sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Assignment sx={{ mr: 2, color: 'success.main', fontSize: 28 }} />
                <Typography variant="h6" fontWeight={600} color="success.main">
                  테스트 시나리오 생성
                </Typography>
              </Box>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3, flexGrow: 1 }}>
                VCS 저장소의 변경 사항을 분석하여 테스트 시나리오를 생성합니다.
              </Typography>
              
              <Button
                variant="contained"
                size="large"
                onClick={handleBasicGenerate}
                disabled={isGenerating || workflowState !== 'idle' || !repoPath.trim()}
                startIcon={<Rocket />}
                fullWidth
                sx={{
                  py: 1.5,
                  background: isGenerating 
                    ? 'linear-gradient(45deg, #bdbdbd 30%, #9e9e9e 90%)' 
                    : 'linear-gradient(45deg, #4caf50 30%, #388e3c 90%)',
                  boxShadow: '0 4px 12px rgba(76, 175, 80, 0.3)',
                  '&:hover': {
                    background: 'linear-gradient(45deg, #388e3c 30%, #2e7d32 90%)',
                  }
                }}
              >
                {isGenerating ? '생성 중...' : '시나리오 생성'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Phase 3: 전체 문서 생성 */}
        <Grid item xs={12} md={6}>
          <Card 
            sx={{ 
              height: '100%',
              background: 'linear-gradient(135deg, #fff3e0 0%, #ffffff 100%)',
              border: '2px solid rgba(255, 152, 0, 0.2)'
            }}
          >
            <CardContent sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Article sx={{ mr: 2, color: 'warning.main', fontSize: 28 }} />
                <Typography variant="h6" fontWeight={600} color="warning.main">
                  전체 문서 생성
                </Typography>
                <Chip 
                  label="Phase 3" 
                  size="small" 
                  sx={{ 
                    ml: 1,
                    backgroundColor: 'warning.main',
                    color: 'white',
                    fontWeight: 600
                  }}
                />
              </Box>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                HTML 파일과 VCS 저장소를 분석하여 변경관리 문서, 테스트 시나리오를 모두 생성합니다.
              </Typography>
              
              <input
                ref={fileInputRef}
                type="file"
                accept=".html,text/html"
                style={{ display: 'none' }}
                onChange={handleFileSelect}
              />
              
              <Button
                variant="outlined"
                onClick={() => fileInputRef.current?.click()}
                disabled={workflowState !== 'idle'}
                startIcon={<CloudUpload />}
                fullWidth
                sx={{ mb: 2 }}
              >
                {htmlFile ? htmlFile.name : 'HTML 파일 선택'}
              </Button>
              
              <Button
                variant="contained"
                size="large"
                onClick={handleFullGeneration}
                disabled={workflowState !== 'idle' || !repoPath.trim() || !htmlFile}
                startIcon={<Description />}
                fullWidth
                sx={{
                  py: 1.5,
                  background: workflowState !== 'idle'
                    ? 'linear-gradient(45deg, #bdbdbd 30%, #9e9e9e 90%)' 
                    : 'linear-gradient(45deg, #ff9800 30%, #f57c00 90%)',
                  boxShadow: '0 4px 12px rgba(255, 152, 0, 0.3)',
                  '&:hover': {
                    background: 'linear-gradient(45deg, #f57c00 30%, #ef6c00 90%)',
                  }
                }}
              >
                {workflowState !== 'idle' ? getWorkflowStateMessage() : '전체 문서 생성'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Phase 3 진행 상황 표시 */}
      {workflowState !== 'idle' && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              {getWorkflowStateIcon()}
              <Typography variant="h6" sx={{ ml: 2 }}>
                {getWorkflowStateMessage()}
              </Typography>
            </Box>
            
            {fullGenProgress && (
              <Box>
                <LinearProgress
                  variant="determinate"
                  value={fullGenProgress.progress}
                  sx={{ mb: 2, height: 10, borderRadius: 5 }}
                />
                <Typography variant="body2" color="text.secondary">
                  {fullGenProgress.message}
                </Typography>
                {fullGenProgress.current_step && (
                  <Typography variant="caption" color="text.secondary">
                    현재 단계: {fullGenProgress.current_step} ({fullGenProgress.steps_completed}/{fullGenProgress.total_steps})
                  </Typography>
                )}
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Phase 3 결과 및 다운로드 */}
      {fullGenResult && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h5" sx={{ mb: 3, color: 'success.main' }}>
              ✅ 문서 생성 완료!
            </Typography>
            
            <Grid container spacing={2}>
              {fullGenResult.download_urls.word && (
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    variant="outlined"
                    fullWidth
                    startIcon={<Description />}
                    href={fullGenResult.download_urls.word}
                    download
                  >
                    변경관리 요청서
                  </Button>
                </Grid>
              )}
              
              {fullGenResult.download_urls.excel_list && (
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    variant="outlined"
                    fullWidth
                    startIcon={<ListAlt />}
                    href={fullGenResult.download_urls.excel_list}
                    download
                  >
                    변경요청 목록
                  </Button>
                </Grid>
              )}
              
              {fullGenResult.download_urls.base_scenario && (
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    variant="outlined"
                    fullWidth
                    startIcon={<Assignment />}
                    href={fullGenResult.download_urls.base_scenario}
                    download
                  >
                    테스트 시나리오
                  </Button>
                </Grid>
              )}
              
              <Grid item xs={12} sm={6} md={3}>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<Download />}
                  onClick={handleDownloadAll}
                  sx={{
                    background: 'linear-gradient(45deg, #2196f3 30%, #1976d2 90%)',
                  }}
                >
                  전체 다운로드
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* CLI 대기 상태 표시 (기존 기능) */}
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

      {/* 진행 상황 표시 (기존 기능) */}
      {v2Progress && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Psychology sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h6">
                생성 진행 상황
              </Typography>
              <Chip
                label={`${(v2Progress.progress ?? 0).toFixed(0)}%`}
                color="primary"
                sx={{ ml: 'auto' }}
              />
            </Box>
            
            <LinearProgress
              variant="determinate"
              value={v2Progress.progress ?? 0}
              color={getProgressColor()}
              sx={{ height: 10, borderRadius: 5, mb: 2 }}
            />
            
            <Typography variant="body2" color="text.secondary">
              {v2Progress.message}
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* 오류 표시 */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* 결과 표시 (기존 기능) */}
      {result && (
        <Box>
          <ScenarioResultViewer result={result} onFeedback={handleFeedback} />
        </Box>
      )}

      {/* 피드백 모달 (기존 기능) */}
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