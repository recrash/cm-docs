import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Slider,
  Chip
} from '@mui/material'
import { ExpandMore, Send, Cancel } from '@mui/icons-material'
import { feedbackApi } from '../services/api'
import type { ScenarioResponse, TestCaseFeedback } from '../types'
import logger from '../utils/logger'

interface FeedbackModalProps {
  open: boolean
  onClose: () => void
  feedbackType: 'like' | 'dislike'
  result: ScenarioResponse
  repoPath: string
}

const ratingLabels: { [key: number]: string } = {
  1: '매우 나쁨',
  2: '나쁨',
  3: '보통',
  4: '좋음',
  5: '매우 좋음'
}

export default function FeedbackModal({ 
  open, 
  onClose, 
  feedbackType, 
  result, 
  repoPath 
}: FeedbackModalProps) {
  const [comments, setComments] = useState('')
  const [testcaseFeedback, setTestcaseFeedback] = useState<TestCaseFeedback[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  React.useEffect(() => {
    if (open) {
      logger.info(`피드백 모달 열림: type=${feedbackType}, test_cases_count=${result.test_cases.length}`)
      
      // 모달이 열릴 때 테스트케이스 피드백 초기화
      const initialFeedback = result.test_cases.slice(0, 5).map(testCase => ({
        testcase_id: testCase.ID,
        score: 3,
        comments: ''
      }))
      setTestcaseFeedback(initialFeedback)
      setComments('')
      setShowSuccess(false)
      
      logger.debug(`테스트케이스 피드백 초기화: count=${initialFeedback.length}`)
    }
  }, [open, result.test_cases, feedbackType])

  const handleTestcaseRatingChange = (index: number, score: number) => {
    logger.debug(`테스트케이스 평가 변경: index=${index}, score=${score}, label=${ratingLabels[score]}`)
    
    setTestcaseFeedback(prev => 
      prev.map((item, i) => 
        i === index ? { ...item, score } : item
      )
    )
  }

  const handleTestcaseCommentChange = (index: number, comment: string) => {
    logger.debug(`테스트케이스 코멘트 변경: index=${index}, comment_length=${comment.length}`)
    
    setTestcaseFeedback(prev => 
      prev.map((item, i) => 
        i === index ? { ...item, comments: comment } : item
      )
    )
  }

  const handleSubmit = async () => {
    logger.info(`피드백 제출 시작: type=${feedbackType}, comments_length=${comments.length}`)
    
    try {
      setIsSubmitting(true)

      const feedbackRequest = {
        feedback_type: feedbackType,
        comments,
        testcase_feedback: testcaseFeedback.filter(tf => tf.comments || tf.score !== 3),
        repo_path: repoPath,
        git_analysis: `Generated from ${repoPath}`, // 실제로는 Git 분석 결과가 필요
        scenario_content: result
      }

      logger.debug(`피드백 요청 데이터: testcase_feedback_count=${feedbackRequest.testcase_feedback.length}`)

      await feedbackApi.submit(feedbackRequest)
      
      logger.info(`피드백 제출 성공: type=${feedbackType}`)
      setShowSuccess(true)
    } catch (error) {
      logger.error(`피드백 제출 실패: type=${feedbackType}, error=${error}`)
      console.error('Failed to submit feedback:', error)
      alert('피드백 제출 중 오류가 발생했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    logger.info(`피드백 모달 닫힘: type=${feedbackType}`)
    
    setComments('')
    setTestcaseFeedback([])
    setShowSuccess(false)
    onClose()
  }

  if (showSuccess) {
    return (
      <Dialog 
        open={open} 
        onClose={handleClose} 
        maxWidth="sm" 
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 4,
            background: 'linear-gradient(135deg, #e8f5e8 0%, #ffffff 100%)',
            border: '2px solid rgba(76, 175, 80, 0.2)'
          }
        }}
      >
        <DialogContent sx={{ textAlign: 'center', py: 6, px: 4 }}>
          <Box sx={{ mb: 4 }}>
            <Box 
              sx={{ 
                width: 80, 
                height: 80, 
                borderRadius: '50%', 
                background: 'linear-gradient(45deg, #4caf50 30%, #388e3c 90%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mx: 'auto',
                mb: 3,
                boxShadow: '0 8px 24px rgba(76, 175, 80, 0.3)'
              }}
            >
              <Typography sx={{ fontSize: '2.5rem' }}>🎉</Typography>
            </Box>
            <Typography variant="h4" fontWeight={700} color="success.main" gutterBottom>
              피드백 제출 완료!
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.6 }}>
              귀하의 소중한 의견이 시스템 개선에 활용됩니다.
            </Typography>
          </Box>
          
          {comments && (
            <Box 
              sx={{ 
                p: 3,
                backgroundColor: 'rgba(33, 150, 243, 0.08)',
                borderRadius: 3,
                border: '1px solid rgba(33, 150, 243, 0.2)',
                mb: 3
              }}
            >
              <Typography variant="subtitle2" color="primary.main" fontWeight={600} sx={{ mb: 1 }}>
                제출된 의견:
              </Typography>
              <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                "{comments.slice(0, 80)}{comments.length > 80 ? '...' : ''}"
              </Typography>
            </Box>
          )}
        </DialogContent>
        
        <DialogActions sx={{ p: 4, pt: 0 }}>
          <Button 
            onClick={handleClose} 
            variant="contained" 
            fullWidth
            size="large"
            sx={{
              py: 2,
              fontSize: '1.1rem',
              fontWeight: 700,
              background: 'linear-gradient(45deg, #4caf50 30%, #388e3c 90%)',
              '&:hover': {
                background: 'linear-gradient(45deg, #388e3c 30%, #2e7d32 90%)',
                transform: 'translateY(-1px)'
              }
            }}
          >
            확인
          </Button>
        </DialogActions>
      </Dialog>
    )
  }

  return (
    <Dialog 
      open={open} 
      onClose={handleClose} 
      maxWidth="md" 
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 4,
          background: 'linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%)',
          border: '2px solid rgba(33, 150, 243, 0.1)'
        }
      }}
    >
      <DialogTitle 
        sx={{ 
          p: 4, 
          pb: 2,
          background: feedbackType === 'like' 
            ? 'linear-gradient(135deg, #e8f5e8 0%, #ffffff 100%)'
            : 'linear-gradient(135deg, #ffebee 0%, #ffffff 100%)',
          borderBottom: '1px solid rgba(0, 0, 0, 0.06)'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box 
            sx={{ 
              width: 48, 
              height: 48, 
              borderRadius: '50%', 
              background: feedbackType === 'like' 
                ? 'linear-gradient(45deg, #4caf50 30%, #388e3c 90%)'
                : 'linear-gradient(45deg, #f44336 30%, #d32f2f 90%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mr: 2,
              boxShadow: feedbackType === 'like'
                ? '0 4px 12px rgba(76, 175, 80, 0.3)'
                : '0 4px 12px rgba(244, 67, 54, 0.3)'
            }}
          >
            <Typography sx={{ fontSize: '1.5rem' }}>
              {feedbackType === 'like' ? '👍' : '👎'}
            </Typography>
          </Box>
          <Typography variant="h5" fontWeight={700} color={feedbackType === 'like' ? 'success.main' : 'error.main'}>
            {feedbackType === 'like' ? '긍정적 피드백' : '개선 제안'}
          </Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent sx={{ p: 4 }}>
        <Box 
          sx={{ 
            p: 3,
            backgroundColor: 'rgba(33, 150, 243, 0.04)',
            borderRadius: 3,
            border: '1px solid rgba(33, 150, 243, 0.1)',
            mb: 4
          }}
        >
          <Typography variant="body1" color="primary.main" sx={{ lineHeight: 1.6 }}>
            새로 생성된 시나리오에 대한 의견을 주세요 (선택 사항)
          </Typography>
        </Box>

        <Typography variant="h6" fontWeight={600} color="text.primary" gutterBottom sx={{ mb: 2 }}>
          {feedbackType === 'like' 
            ? '어떤 점이 도움이 되었나요?' 
            : '어떤 점이 아쉬웠나요?'
          }
        </Typography>

        <TextField
          fullWidth
          multiline
          rows={4}
          value={comments}
          onChange={(e) => {
            logger.debug(`전체 코멘트 변경: length=${e.target.value.length}`)
            setComments(e.target.value)
          }}
          placeholder={
            feedbackType === 'like'
              ? '예: 시나리오가 구체적이고 실용적이었습니다.'
              : '예: 테스트 절차가 불명확하거나 실제 환경과 맞지 않았습니다.'
          }
          helperText="귀하의 피드백은 향후 더 나은 시나리오 생성에 활용됩니다."
          sx={{ 
            mb: 4,
            '& .MuiOutlinedInput-root': {
              backgroundColor: 'rgba(255, 255, 255, 0.8)',
              borderRadius: 3,
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 1)'
              }
            }
          }}
        />

        {/* 개별 테스트케이스 평가 */}
        <Accordion 
          sx={{
            borderRadius: 3,
            border: '2px solid rgba(33, 150, 243, 0.1)',
            '&:before': {
              display: 'none'
            }
          }}
        >
          <AccordionSummary 
            expandIcon={<ExpandMore />}
            sx={{
              background: 'linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%)',
              borderRadius: '12px 12px 0 0',
              '&.Mui-expanded': {
                borderRadius: '12px 12px 0 0'
              }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Box 
                sx={{ 
                  width: 32, 
                  height: 32, 
                  borderRadius: '50%', 
                  background: 'linear-gradient(45deg, #ff9800 30%, #f57c00 90%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mr: 2
                }}
              >
                <Typography sx={{ fontSize: '1rem' }}>📝</Typography>
              </Box>
              <Typography variant="h6" fontWeight={600} color="primary.main">
                개별 테스트케이스 평가 (선택사항)
              </Typography>
            </Box>
          </AccordionSummary>
          
          <AccordionDetails sx={{ p: 4 }}>
            <Box 
              sx={{ 
                p: 2,
                backgroundColor: 'rgba(255, 193, 7, 0.04)',
                borderRadius: 2,
                border: '1px solid rgba(255, 193, 7, 0.2)',
                mb: 3
              }}
            >
              <Typography variant="body1" color="warning.main" sx={{ lineHeight: 1.6 }}>
                각 테스트케이스에 대한 구체적인 평가를 남겨주세요.
              </Typography>
            </Box>

            {testcaseFeedback.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                평가할 테스트케이스가 없습니다.
              </Typography>
            ) : (
              <Box>
                {testcaseFeedback.map((feedback, index) => {
                  const testCase = result.test_cases[index]
                  if (!testCase) return null

                  const truncatedDesc = testCase.절차.length > 50 
                    ? testCase.절차.slice(0, 50) + '...'
                    : testCase.절차

                  return (
                    <Box 
                      key={index} 
                      sx={{ 
                        mb: 3, 
                        p: 3, 
                        background: 'linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%)',
                        border: '2px solid rgba(33, 150, 243, 0.1)', 
                        borderRadius: 3,
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
                      }}
                    >
                      <Typography variant="subtitle2" gutterBottom>
                        <Chip label={testCase.ID} size="small" sx={{ mr: 1 }} />
                        {truncatedDesc}
                      </Typography>

                      <Grid container spacing={2} alignItems="center">
                        <Grid item xs={12} sm={6}>
                          <Typography variant="caption" color="text.secondary">
                            평가 ({ratingLabels[feedback.score]})
                          </Typography>
                          <Slider
                            value={feedback.score}
                            onChange={(_, value) => handleTestcaseRatingChange(index, value as number)}
                            step={1}
                            marks
                            min={1}
                            max={5}
                            valueLabelDisplay="auto"
                            valueLabelFormat={(value) => ratingLabels[value]}
                          />
                        </Grid>
                        
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            size="small"
                            value={feedback.comments}
                            onChange={(e) => handleTestcaseCommentChange(index, e.target.value)}
                            placeholder="이 테스트케이스에 대한 구체적인 의견..."
                            variant="outlined"
                          />
                        </Grid>
                      </Grid>
                    </Box>
                  )
                })}
              </Box>
            )}
          </AccordionDetails>
        </Accordion>
      </DialogContent>

      <DialogActions sx={{ p: 4, pt: 2, gap: 2, borderTop: '1px solid rgba(0, 0, 0, 0.06)' }}>
        <Button
          onClick={handleClose}
          disabled={isSubmitting}
          startIcon={<Cancel />}
          variant="outlined"
          size="large"
          sx={{
            borderWidth: 2,
            '&:hover': {
              borderWidth: 2,
              backgroundColor: 'rgba(0, 0, 0, 0.04)'
            }
          }}
        >
          취소
        </Button>
        
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting}
          variant="contained"
          startIcon={<Send />}
          size="large"
          sx={{
            flex: 1,
            py: 1.5,
            fontSize: '1rem',
            fontWeight: 700,
            background: 'linear-gradient(45deg, #2196f3 30%, #1976d2 90%)',
            '&:hover': {
              background: 'linear-gradient(45deg, #1976d2 30%, #1565c0 90%)',
              transform: 'translateY(-1px)'
            },
            '&:disabled': {
              background: 'linear-gradient(45deg, #bdbdbd 30%, #9e9e9e 90%)'
            }
          }}
        >
          {isSubmitting ? '제출 중...' : '제출'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}