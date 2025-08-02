import React, { useState, useEffect } from 'react'
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
  AccordionDetails
} from '@mui/material'
import {
  ExpandMore,
  Psychology,
  Refresh,
  Clear,
  Storage,
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

  useEffect(() => {
    loadRagInfo()
  }, [ragStatus])

  const loadRagInfo = async () => {
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
  }

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
    } catch (error: any) {
      setMessage(`인덱싱 중 오류 발생: ${error.message}`)
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
    } catch (error: any) {
      setMessage(`데이터베이스 초기화 중 오류 발생: ${error.message}`)
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
    <Accordion sx={{ mb: 3 }}>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
          <Psychology color="primary" />
          <Typography variant="h6">RAG 시스템 정보</Typography>
          <Chip
            label={getStatusText()}
            color={getStatusColor()}
            size="small"
            variant="outlined"
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
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={3}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    벡터 DB 상태
                  </Typography>
                  <Typography variant="h6">
                    {getStatusText()}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={3}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    저장된 문서 수
                  </Typography>
                  <Typography variant="h6">
                    {ragStatus.document_count}개
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={3}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    임베딩 모델
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {ragStatus.embedding_model}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={3}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    청크 크기
                  </Typography>
                  <Typography variant="h6">
                    {ragStatus.chunk_size}자
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {/* 문서 정보 */}
            {ragInfo?.documents.enabled && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  <Description fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                  문서 폴더 정보
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        폴더 경로
                      </Typography>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          wordBreak: 'break-all',
                          fontSize: '0.875rem',
                          fontFamily: 'monospace'
                        }}
                      >
                        {ragInfo.documents.folder_path || 'Unknown'}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        지원 파일
                      </Typography>
                      <Typography variant="body2">
                        {ragInfo.documents.supported_files}개 / {ragInfo.documents.total_files}개
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        파일 유형
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {Object.entries(ragInfo.documents.file_types).map(([ext, count]) => (
                          <Chip
                            key={ext}
                            label={`${ext}(${count})`}
                            size="small"
                            variant="outlined"
                          />
                        ))}
                      </Box>
                    </Box>
                  </Grid>
                </Grid>
              </Box>
            )}

            {/* 액션 버튼들 */}
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={isIndexing ? <CircularProgress size={16} /> : <Description />}
                  onClick={() => handleIndexDocuments(false)}
                  disabled={isIndexing || isClearing}
                >
                  문서 인덱싱
                </Button>
              </Grid>
              <Grid item xs={12} md={4}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={isIndexing ? <CircularProgress size={16} /> : <Refresh />}
                  onClick={() => handleIndexDocuments(true)}
                  disabled={isIndexing || isClearing}
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
                >
                  벡터 DB 초기화
                </Button>
              </Grid>
            </Grid>

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