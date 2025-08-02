import React from 'react'
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
  Chip
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
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            📊 생성 결과 미리보기
          </Typography>
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              개요
            </Typography>
            <Typography variant="body1">
              {result.scenario_description}
            </Typography>
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" color="text.secondary">
              제목
            </Typography>
            <Typography variant="body1" fontWeight="bold">
              {result.test_scenario_name}
            </Typography>
          </Box>

          {/* Excel 다운로드 버튼 */}
          {result.metadata?.excel_filename && (
            <Box sx={{ mb: 3 }}>
              <Button
                variant="contained"
                startIcon={<Download />}
                onClick={handleDownload}
                color="primary"
                sx={{ 
                  bgcolor: 'success.main',
                  '&:hover': { bgcolor: 'success.dark' }
                }}
              >
                Excel 파일 다운로드 📥
              </Button>
            </Box>
          )}

          {/* 피드백 버튼 */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              📝 시나리오 평가 및 피드백
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              생성된 시나리오에 대한 평가를 남겨주시면 향후 더 나은 시나리오 생성에 도움이 됩니다.
            </Typography>
            
            <Typography variant="subtitle2" gutterBottom>
              이 시나리오가 도움이 되었나요?
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                startIcon={<ThumbUp />}
                onClick={() => onFeedback('like')}
                color="primary"
              >
                좋아요
              </Button>
              <Button
                variant="outlined"
                startIcon={<ThumbDown />}
                onClick={() => onFeedback('dislike')}
                color="error"
              >
                개선 필요
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 테스트 케이스 테이블 */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            테스트 케이스 ({result.test_cases.length}개)
          </Typography>
          
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: 'grey.50' }}>
                  <TableCell sx={{ fontWeight: 'bold' }}>ID</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>절차</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>사전조건</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>데이터</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>예상결과</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Unit</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Integration</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {result.test_cases.map((testCase: TestCase, index: number) => (
                  <TableRow key={index} hover>
                    <TableCell sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                      {testCase.ID}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {formatText(testCase.절차)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {formatText(testCase.사전조건)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {formatText(testCase.데이터)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {formatText(testCase.예상결과)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {testCase.Unit ? (
                        <Chip 
                          label="Y" 
                          size="small" 
                          variant="filled"
                          color="primary"
                        />
                      ) : (
                        <Typography variant="body2" color="text.disabled">-</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {testCase.Integration ? (
                        <Chip 
                          label="Y" 
                          size="small" 
                          variant="filled"
                          color="secondary"
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