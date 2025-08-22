import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper
} from '@mui/material'
import {
  ExpandMore,
  Psychology,
  Refresh,
  Clear,
  Description
} from '@mui/icons-material'
import { ragApi } from '../services/api'
import type { RAGInfo, RAGStatus, IndexingResult } from '../types'

interface RAGSystemPanelProps {
  ragStatus: RAGStatus | null
  onStatusUpdate: () => void
}

export default function RAGSystemPanel({ ragStatus, onStatusUpdate }: RAGSystemPanelProps) {
  const [ragInfo, setRagInfo] = useState<RAGInfo | null>(null)
  const [isIndexing, setIsIndexing] = useState(false)
  const [isClearing, setIsClearing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [messageType, setMessageType] = useState<'success' | 'error' | 'info'>('info')

  const loadRagInfo = useCallback(async () => {
    if (!ragStatus || ragStatus.status === 'error') return
    
    try {
      setLoading(true)
      const info = await ragApi.getInfo()
      setRagInfo(info)
    } catch (error) {
      console.error('Failed to load RAG info:', error)
    } finally {
      setLoading(false)
    }
  }, [ragStatus])

  useEffect(() => {
    loadRagInfo()
  }, [loadRagInfo])

  const handleIndexDocuments = async (forceReindex: boolean = false) => {
    try {
      setIsIndexing(true)
      setMessage(null)
      
      const result: IndexingResult = await ragApi.indexDocuments(forceReindex)
      
      if (result.status === 'success') {
        setMessage(`인덱싱 완료! ${result.indexed_count}개 파일, ${result.total_chunks_added}개 청크 추가`)
        setMessageType('success')
        onStatusUpdate()
        loadRagInfo()
      } else {
        setMessage(`인덱싱 실패: ${result.message || 'Unknown error'}`)
        setMessageType('error')
      }
    } catch (error) {
      setMessage(`인덱싱 중 오류 발생: ${error instanceof Error ? error.message : '알 수 없는 오류'}`)
      setMessageType('error')
    } finally {
      setIsIndexing(false)
    }
  }

  const handleClearDatabase = async () => {
    try {
      setIsClearing(true)
      setMessage(null)
      
      await ragApi.clearDatabase()
      
      setMessage('벡터 데이터베이스가 성공적으로 초기화되었습니다.')
      setMessageType('success')
      onStatusUpdate()
      loadRagInfo()
    } catch (error) {
      setMessage(`데이터베이스 초기화 중 오류 발생: ${error instanceof Error ? error.message : '알 수 없는 오류'}`)
      setMessageType('error')
    } finally {
      setIsClearing(false)
    }
  }

  const getStatusColor = () => {
    if (!ragStatus) return 'default'
    switch (ragStatus.status) {
      case 'active': return 'success'
      case 'inactive': return 'warning'
      case 'error': return 'error'
      default: return 'default'
    }
  }

  const getStatusText = () => {
    if (!ragStatus) return '로딩 중...'
    switch (ragStatus.status) {
      case 'active': return '정상 작동'
      case 'inactive': return '비활성화'
      case 'error': return '오류'
      default: return '알 수 없음'
    }
  }

  if (!ragStatus) {
    return (
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <CircularProgress size={20} />
            <Typography>RAG 시스템 상태 로딩 중...</Typography>
          </Box>
        </CardContent>
      </Card>
    )
  }

  if (ragStatus.status === 'error') {
    return (
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Alert severity="error">
            ⚠️ RAG 시스템이 비활성화되어 있거나 초기화에 실패했습니다. 
            config.json에서 RAG를 활성화하고 앱을 재시작해주세요.
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <Accordion 
      sx={{ 
        mb: 4,
        borderRadius: 4,
        border: '2px solid rgba(156, 39, 176, 0.1)',
        background: 'linear-gradient(135deg, #f3e5f5 0%, #ffffff 100%)',
        '&:before': {
          display: 'none'
        },
        '&.Mui-expanded': {
          margin: 0,
          mb: 4
        }
      }}
    >
      <AccordionSummary 
        expandIcon={<ExpandMore />}
        sx={{
          p: 3,
          '&.Mui-expanded': {
            minHeight: 72
          }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
          <Box 
            sx={{ 
              width: 48, 
              height: 48, 
              borderRadius: '50%', 
              background: 'linear-gradient(45deg, #9c27b0 30%, #7b1fa2 90%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(156, 39, 176, 0.3)'
            }}
          >
            <Psychology sx={{ color: 'white', fontSize: 24 }} />
          </Box>
          <Typography variant="h5" fontWeight={700} color="secondary.main" sx={{ flexGrow: 1 }}>
            RAG 시스템 정보
          </Typography>
          <Chip
            label={getStatusText()}
            color={getStatusColor()}
            sx={{
              fontWeight: 600,
              px: 2,
              py: 1,
              fontSize: '0.875rem'
            }}
          />
        </Box>
      </AccordionSummary>
      
      <AccordionDetails>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box>
            {/* 상태 정보 */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid item xs={12} md={3}>
                <Paper 
                  elevation={0}
                  sx={{ 
                    textAlign: 'center', 
                    p: 3,
                    background: 'linear-gradient(135deg, #e8f5e8 0%, #ffffff 100%)',
                    border: '2px solid rgba(76, 175, 80, 0.2)',
                    borderRadius: 3,
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 8px 24px rgba(76, 175, 80, 0.2)'
                    }
                  }}
                >
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    📊 벡터 DB 상태
                  </Typography>
                  <Typography variant="h5" fontWeight={700} color="success.main">
                    {getStatusText()}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper 
                  elevation={0}
                  sx={{ 
                    textAlign: 'center', 
                    p: 3,
                    background: 'linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%)',
                    border: '2px solid rgba(33, 150, 243, 0.2)',
                    borderRadius: 3,
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 8px 24px rgba(33, 150, 243, 0.2)'
                    }
                  }}
                >
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    📚 저장된 문서 수
                  </Typography>
                  <Typography variant="h5" fontWeight={700} color="primary.main">
                    {ragStatus.document_count}개
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper 
                  elevation={0}
                  sx={{ 
                    textAlign: 'center', 
                    p: 3,
                    background: 'linear-gradient(135deg, #fff3e0 0%, #ffffff 100%)',
                    border: '2px solid rgba(255, 152, 0, 0.2)',
                    borderRadius: 3,
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 8px 24px rgba(255, 152, 0, 0.2)'
                    }
                  }}
                >
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    🤖 임베딩 모델
                  </Typography>
                  <Typography variant="body1" fontWeight={700} color="warning.main" sx={{ fontSize: '0.9rem' }}>
                    {ragStatus.embedding_model}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper 
                  elevation={0}
                  sx={{ 
                    textAlign: 'center', 
                    p: 3,
                    background: 'linear-gradient(135deg, #f3e5f5 0%, #ffffff 100%)',
                    border: '2px solid rgba(156, 39, 176, 0.2)',
                    borderRadius: 3,
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 8px 24px rgba(156, 39, 176, 0.2)'
                    }
                  }}
                >
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    🧩 청크 크기
                  </Typography>
                  <Typography variant="h5" fontWeight={700} color="secondary.main">
                    {ragStatus.chunk_size}자
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* 문서 정보 */}
            {ragInfo?.documents.enabled && (
              <Box 
                sx={{ 
                  mb: 4,
                  p: 3,
                  background: 'linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%)',
                  border: '2px solid rgba(33, 150, 243, 0.1)',
                  borderRadius: 3
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                  <Box 
                    sx={{ 
                      width: 40, 
                      height: 40, 
                      borderRadius: '50%', 
                      background: 'linear-gradient(45deg, #2196f3 30%, #1976d2 90%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mr: 2
                    }}
                  >
                    <Description sx={{ color: 'white', fontSize: 20 }} />
                  </Box>
                  <Typography variant="h6" fontWeight={600} color="primary.main">
                    문서 폴더 정보
                  </Typography>
                </Box>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <Box 
                      sx={{ 
                        p: 2,
                        backgroundColor: 'rgba(0, 0, 0, 0.02)',
                        borderRadius: 2,
                        border: '1px solid rgba(0, 0, 0, 0.08)'
                      }}
                    >
                      <Typography variant="subtitle2" color="primary.main" fontWeight={600} sx={{ mb: 1 }}>
                        📁 폴더 경로
                      </Typography>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          wordBreak: 'break-all',
                          fontSize: '0.875rem',
                          fontFamily: 'monospace',
                          background: 'rgba(33, 150, 243, 0.08)',
                          p: 1,
                          borderRadius: 1,
                          border: '1px solid rgba(33, 150, 243, 0.2)'
                        }}
                      >
                        {ragInfo.documents.folder_path || 'Unknown'}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Paper 
                      elevation={0}
                      sx={{ 
                        p: 2,
                        background: 'linear-gradient(135deg, #e8f5e8 0%, #ffffff 100%)',
                        border: '1px solid rgba(76, 175, 80, 0.2)',
                        borderRadius: 2
                      }}
                    >
                      <Typography variant="subtitle2" color="success.main" fontWeight={600} sx={{ mb: 1 }}>
                        📊 지원 파일
                      </Typography>
                      <Typography variant="h6" fontWeight={700} color="success.main">
                        {ragInfo.documents.supported_files}개 / {ragInfo.documents.total_files}개
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Paper 
                      elevation={0}
                      sx={{ 
                        p: 2,
                        background: 'linear-gradient(135deg, #fff3e0 0%, #ffffff 100%)',
                        border: '1px solid rgba(255, 152, 0, 0.2)',
                        borderRadius: 2
                      }}
                    >
                      <Typography variant="subtitle2" color="warning.main" fontWeight={600} sx={{ mb: 1 }}>
                        📝 파일 유형
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {Object.entries(ragInfo.documents.file_types).map(([ext, count]) => (
                          <Chip
                            key={ext}
                            label={`${ext}(${count})`}
                            size="small"
                            sx={{
                              background: 'linear-gradient(45deg, #ff9800 30%, #f57c00 90%)',
                              color: 'white',
                              fontWeight: 600
                            }}
                          />
                        ))}
                      </Box>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>
            )}

            {/* 액션 버튼들 */}
            <Box 
              sx={{ 
                p: 3,
                background: 'linear-gradient(135deg, #f3e5f5 0%, #ffffff 100%)',
                border: '2px solid rgba(156, 39, 176, 0.1)',
                borderRadius: 3,
                mb: 3
              }}
            >
              <Typography variant="h6" fontWeight={600} color="secondary.main" sx={{ mb: 3 }}>
                ⚙️ 작업 관리
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <Button
                    fullWidth
                    variant="contained"
                    startIcon={isIndexing ? <CircularProgress size={16} color="inherit" /> : <Description />}
                    onClick={() => handleIndexDocuments(false)}
                    disabled={isIndexing || isClearing}
                    sx={{
                      py: 1.5,
                      background: 'linear-gradient(45deg, #2196f3 30%, #1976d2 90%)',
                      '&:hover': {
                        background: 'linear-gradient(45deg, #1976d2 30%, #1565c0 90%)'
                      },
                      '&:disabled': {
                        background: 'linear-gradient(45deg, #bdbdbd 30%, #9e9e9e 90%)'
                      }
                    }}
                  >
                    문서 인덱싱
                  </Button>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Button
                    fullWidth
                    variant="contained"
                    startIcon={isIndexing ? <CircularProgress size={16} color="inherit" /> : <Refresh />}
                    onClick={() => handleIndexDocuments(true)}
                    disabled={isIndexing || isClearing}
                    sx={{
                      py: 1.5,
                      background: 'linear-gradient(45deg, #ff9800 30%, #f57c00 90%)',
                      '&:hover': {
                        background: 'linear-gradient(45deg, #f57c00 30%, #ef6c00 90%)'
                      },
                      '&:disabled': {
                        background: 'linear-gradient(45deg, #bdbdbd 30%, #9e9e9e 90%)'
                      }
                    }}
                  >
                    전체 재인덱싱
                  </Button>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Button
                    fullWidth
                    variant="outlined"
                    color="error"
                    startIcon={isClearing ? <CircularProgress size={16} /> : <Clear />}
                    onClick={handleClearDatabase}
                    disabled={isIndexing || isClearing}
                    sx={{
                      py: 1.5,
                      borderWidth: 2,
                      '&:hover': {
                        borderWidth: 2,
                        backgroundColor: 'rgba(244, 67, 54, 0.04)'
                      }
                    }}
                  >
                    벡터 DB 초기화
                  </Button>
                </Grid>
              </Grid>
            </Box>

            {/* 메시지 표시 */}
            {message && (
              <Alert severity={messageType} sx={{ mt: 2 }}>
                {message}
              </Alert>
            )}
          </Box>
        )}
      </AccordionDetails>
    </Accordion>
  )
}