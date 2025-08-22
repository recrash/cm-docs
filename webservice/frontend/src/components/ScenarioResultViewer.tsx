import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Grid
} from '@mui/material'
import { ThumbUp, ThumbDown, Download } from '@mui/icons-material'
import { filesApi } from '../services/api'
import type { ScenarioResponse, TestCase } from '../types'

interface ScenarioResultViewerProps {
  result: ScenarioResponse
  onFeedback: (type: 'like' | 'dislike') => void
}

export default function ScenarioResultViewer({ result, onFeedback }: ScenarioResultViewerProps) {
  // 텍스트에서 \n을 실제 줄바꿈으로 변환
  const formatText = (text: string) => {
    return text.replace(/\\n/g, '\n')
  }

  // Excel 파일 다운로드
  const handleDownload = async () => {
    const excelFilename = result.metadata?.excel_filename
    if (!excelFilename) {
      alert('다운로드할 Excel 파일이 없습니다.')
      return
    }

    try {
      // 파일명에서 outputs/ 접두사 제거 (백엔드에서 처리하지만 안전장치)
      const cleanFilename = excelFilename.replace(/^outputs\//, '')
      
      // filesApi를 사용하여 다운로드 URL 생성
      const downloadUrl = filesApi.downloadExcelFile(cleanFilename)
      const response = await fetch(downloadUrl)
      
      if (!response.ok) {
        throw new Error(`파일 다운로드 실패: ${response.status} ${response.statusText}`)
      }

      // Content-Type 확인
      const contentType = response.headers.get('content-type')
      if (!contentType?.includes('spreadsheetml') && !contentType?.includes('excel')) {
        throw new Error('올바른 Excel 파일이 아닙니다.')
      }

      // Blob으로 변환하여 다운로드
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = cleanFilename.split('/').pop() || 'test_scenario.xlsx'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Excel 파일 다운로드 중 오류:', error)
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류'
      alert(`Excel 파일 다운로드에 실패했습니다: ${errorMessage}`)
    }
  }

  return (
    <Box>
      {/* 시나리오 개요 */}
      <Card 
        sx={{ 
          mb: 4,
          background: 'linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%)',
          border: '2px solid rgba(33, 150, 243, 0.1)',
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
              <Typography sx={{ fontSize: '1.5rem' }}>📊</Typography>
            </Box>
            <Typography variant="h5" fontWeight={700} color="primary.main">
              생성 결과 미리보기
            </Typography>
          </Box>
          
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12}>
              <Box 
                sx={{ 
                  p: 3,
                  backgroundColor: 'rgba(33, 150, 243, 0.04)',
                  borderRadius: 3,
                  border: '1px solid rgba(33, 150, 243, 0.1)'
                }}
              >
                <Typography variant="subtitle1" color="primary.main" fontWeight={600} sx={{ mb: 2 }}>
                  🎯 시나리오 제목
                </Typography>
                <Typography variant="h6" fontWeight={700} sx={{ mb: 3 }}>
                  {result.test_scenario_name}
                </Typography>
                
                <Typography variant="subtitle1" color="primary.main" fontWeight={600} sx={{ mb: 2 }}>
                  📝 시나리오 개요
                </Typography>
                <Typography variant="body1" sx={{ lineHeight: 1.8 }}>
                  {result.scenario_description}
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {/* Excel 다운로드 버튼 */}
          {result.metadata?.excel_filename && (
            <Box sx={{ mb: 4 }}>
              <Button
                variant="contained"
                size="large"
                startIcon={<Download />}
                onClick={handleDownload}
                sx={{
                  py: 2,
                  px: 4,
                  fontSize: '1.1rem',
                  fontWeight: 700,
                  background: 'linear-gradient(45deg, #4caf50 30%, #388e3c 90%)',
                  boxShadow: '0 6px 20px rgba(76, 175, 80, 0.3)',
                  '&:hover': {
                    background: 'linear-gradient(45deg, #388e3c 30%, #2e7d32 90%)',
                    boxShadow: '0 8px 25px rgba(76, 175, 80, 0.4)',
                    transform: 'translateY(-2px)'
                  }
                }}
              >
                Excel 파일 다운로드 📥
              </Button>
            </Box>
          )}

          {/* 피드백 버튼 */}
          <Box 
            sx={{ 
              p: 3,
              backgroundColor: 'rgba(255, 193, 7, 0.04)',
              borderRadius: 3,
              border: '1px solid rgba(255, 193, 7, 0.2)',
              mb: 2
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box 
                sx={{ 
                  width: 40, 
                  height: 40, 
                  borderRadius: '50%', 
                  background: 'linear-gradient(45deg, #ff9800 30%, #f57c00 90%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mr: 2,
                  boxShadow: '0 3px 10px rgba(255, 152, 0, 0.3)'
                }}
              >
                <Typography sx={{ fontSize: '1.2rem' }}>📝</Typography>
              </Box>
              <Typography variant="h6" fontWeight={600} color="warning.main">
                시나리오 평가 및 피드백
              </Typography>
            </Box>
            
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, lineHeight: 1.6 }}>
              생성된 시나리오에 대한 평가를 남겨주시면 향후 더 나은 시나리오 생성에 도움이 됩니다.
            </Typography>
            
            <Typography variant="subtitle2" gutterBottom sx={{ mb: 2, fontWeight: 600 }}>
              이 시나리오가 도움이 되었나요?
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="contained"
                startIcon={<ThumbUp />}
                onClick={() => onFeedback('like')}
                sx={{
                  background: 'linear-gradient(45deg, #4caf50 30%, #388e3c 90%)',
                  '&:hover': {
                    background: 'linear-gradient(45deg, #388e3c 30%, #2e7d32 90%)',
                    transform: 'translateY(-1px)'
                  }
                }}
              >
                좋아요
              </Button>
              <Button
                variant="outlined"
                startIcon={<ThumbDown />}
                onClick={() => onFeedback('dislike')}
                color="error"
                sx={{
                  borderWidth: 2,
                  '&:hover': {
                    borderWidth: 2,
                    backgroundColor: 'rgba(244, 67, 54, 0.04)',
                    transform: 'translateY(-1px)'
                  }
                }}
              >
                개선 필요
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 테스트 케이스 테이블 */}
      <Card
        sx={{ 
          background: 'linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%)',
          border: '2px solid rgba(33, 150, 243, 0.1)',
          borderRadius: 4
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
            <Box 
              sx={{ 
                width: 48, 
                height: 48, 
                borderRadius: '50%', 
                background: 'linear-gradient(45deg, #ff9800 30%, #f57c00 90%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mr: 2,
                boxShadow: '0 4px 12px rgba(255, 152, 0, 0.3)'
              }}
            >
              <Typography sx={{ fontSize: '1.5rem' }}>📋</Typography>
            </Box>
            <Typography variant="h5" fontWeight={700} color="warning.main">
              테스트 케이스 ({result.test_cases.length}개)
            </Typography>
          </Box>
          
          <TableContainer 
            component={Paper} 
            variant="outlined"
            sx={{
              borderRadius: 3,
              border: '2px solid rgba(33, 150, 243, 0.1)',
              overflow: 'hidden',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)'
            }}
          >
            <Table sx={{ tableLayout: 'fixed' }}>
              <TableHead>
                <TableRow 
                  sx={{ 
                    background: 'linear-gradient(135deg, #2196f3 0%, #1976d2 100%)'
                  }}
                >
                  <TableCell sx={{ 
                    fontWeight: 700, 
                    color: 'black', 
                    fontSize: '0.9rem',
                    width: '100px',
                    minWidth: '100px',
                    whiteSpace: 'nowrap',
                    px: 2
                  }}>
                    ID
                  </TableCell>
                  <TableCell sx={{ 
                    fontWeight: 700, 
                    color: 'black', 
                    fontSize: '0.9rem',
                    width: '25%',
                    whiteSpace: 'nowrap',
                    px: 2
                  }}>
                    절차
                  </TableCell>
                  <TableCell sx={{ 
                    fontWeight: 700, 
                    color: 'black', 
                    fontSize: '0.9rem',
                    width: '20%',
                    whiteSpace: 'nowrap',
                    px: 2
                  }}>
                    사전조건
                  </TableCell>
                  <TableCell sx={{ 
                    fontWeight: 700, 
                    color: 'black', 
                    fontSize: '0.9rem',
                    width: '20%',
                    whiteSpace: 'nowrap',
                    px: 2
                  }}>
                    데이터
                  </TableCell>
                  <TableCell sx={{ 
                    fontWeight: 700, 
                    color: 'black', 
                    fontSize: '0.9rem',
                    width: '25%',
                    whiteSpace: 'nowrap',
                    px: 2
                  }}>
                    예상결과
                  </TableCell>
                  <TableCell sx={{ 
                    fontWeight: 700, 
                    color: 'black', 
                    fontSize: '0.9rem', 
                    textAlign: 'center',
                    width: '80px',
                    minWidth: '80px',
                    whiteSpace: 'nowrap',
                    px: 1
                  }}>
                    Unit
                  </TableCell>
                  <TableCell sx={{ 
                    fontWeight: 700, 
                    color: 'black', 
                    fontSize: '0.9rem', 
                    textAlign: 'center',
                    width: '110px',
                    minWidth: '110px',
                    whiteSpace: 'nowrap',
                    px: 1
                  }}>
                    Integration
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {result.test_cases.map((testCase: TestCase, index: number) => (
                  <TableRow 
                    key={index} 
                    sx={{
                      '&:nth-of-type(even)': {
                        backgroundColor: 'rgba(33, 150, 243, 0.02)',
                      },
                      '&:hover': {
                        backgroundColor: 'rgba(33, 150, 243, 0.08)',
                        transform: 'scale(1.001)',
                        transition: 'all 0.2s ease-in-out'
                      },
                      transition: 'all 0.2s ease-in-out'
                    }}
                  >
                    <TableCell 
                      sx={{ 
                        fontWeight: 700, 
                        color: 'primary.main',
                        fontSize: '0.95rem',
                        borderLeft: '4px solid',
                        borderLeftColor: 'primary.main',
                        px: 2,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}
                    >
                      {testCase.ID}
                    </TableCell>
                    <TableCell sx={{ px: 2 }}>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                          fontSize: '0.875rem',
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 4,
                          WebkitBoxOrient: 'vertical'
                        }}
                      >
                        {formatText(testCase.절차)}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ px: 2 }}>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                          fontSize: '0.875rem',
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: 'vertical'
                        }}
                      >
                        {formatText(testCase.사전조건)}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ px: 2 }}>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                          fontSize: '0.875rem',
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: 'vertical'
                        }}
                      >
                        {formatText(testCase.데이터)}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ px: 2 }}>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                          fontSize: '0.875rem',
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 4,
                          WebkitBoxOrient: 'vertical'
                        }}
                      >
                        {formatText(testCase.예상결과)}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ textAlign: 'center', px: 1 }}>
                      {testCase.Unit ? (
                        <Chip 
                          label="Y" 
                          size="small" 
                          sx={{
                            background: 'linear-gradient(45deg, #4caf50 30%, #388e3c 90%)',
                            color: 'white',
                            fontWeight: 600
                          }}
                        />
                      ) : (
                        <Typography variant="body2" color="text.disabled">-</Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ textAlign: 'center', px: 1 }}>
                      {testCase.Integration ? (
                        <Chip 
                          label="Y" 
                          size="small" 
                          sx={{
                            background: 'linear-gradient(45deg, #ff9800 30%, #f57c00 90%)',
                            color: 'white',
                            fontWeight: 600
                          }}
                        />
                      ) : (
                        <Typography variant="body2" color="text.disabled">-</Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  )
}