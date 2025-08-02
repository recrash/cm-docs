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
  Alert,
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
      // 모달이 열릴 때 테스트케이스 피드백 초기화
      const initialFeedback = result.test_cases.slice(0, 5).map(testCase => ({
        testcase_id: testCase.ID,
        score: 3,
        comments: ''
      }))
      setTestcaseFeedback(initialFeedback)
      setComments('')
      setShowSuccess(false)
    }
  }, [open, result.test_cases])

  const handleTestcaseRatingChange = (index: number, score: number) => {
    setTestcaseFeedback(prev => 
      prev.map((item, i) => 
        i === index ? { ...item, score } : item
      )
    )
  }

  const handleTestcaseCommentChange = (index: number, comment: string) => {
    setTestcaseFeedback(prev => 
      prev.map((item, i) => 
        i === index ? { ...item, comments: comment } : item
      )
    )
  }

  const handleSubmit = async () => {
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

      await feedbackApi.submit(feedbackRequest)
      setShowSuccess(true)
    } catch (error) {
      console.error('Failed to submit feedback:', error)
      alert('피드백 제출 중 오류가 발생했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    setComments('')
    setTestcaseFeedback([])
    setShowSuccess(false)
    onClose()
  }

  if (showSuccess) {
    return (
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogContent sx={{ textAlign: 'center', py: 4 }}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="h4" sx={{ mb: 2 }}>
              🎉
            </Typography>
            <Typography variant="h6" gutterBottom>
              피드백이 성공적으로 제출되었습니다!
            </Typography>
            <Typography variant="body2" color="text.secondary">
              귀하의 소중한 의견이 시스템 개선에 활용됩니다.
            </Typography>
          </Box>
          
          {comments && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="caption">
                <strong>제출된 의견:</strong> {comments.slice(0, 50)}
                {comments.length > 50 ? '...' : ''}
              </Typography>
            </Alert>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleClose} variant="contained" fullWidth>
            확인
          </Button>
        </DialogActions>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {feedbackType === 'like' ? '👍 긍정적 피드백' : '👎 개선 제안'}
      </DialogTitle>
      
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          새로 생성된 시나리오에 대한 의견을 주세요 (선택 사항)
        </Typography>

        <Typography variant="subtitle2" gutterBottom>
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
          onChange={(e) => setComments(e.target.value)}
          placeholder={
            feedbackType === 'like'
              ? '예: 시나리오가 구체적이고 실용적이었습니다.'
              : '예: 테스트 절차가 불명확하거나 실제 환경과 맞지 않았습니다.'
          }
          helperText="귀하의 피드백은 향후 더 나은 시나리오 생성에 활용됩니다."
          sx={{ mb: 3 }}
        />

        {/* 개별 테스트케이스 평가 */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="subtitle2">
              개별 테스트케이스 평가 (선택사항)
            </Typography>
          </AccordionSummary>
          
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              각 테스트케이스에 대한 구체적인 평가를 남겨주세요.
            </Typography>

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
                    <Box key={index} sx={{ mb: 3, p: 2, border: 1, borderColor: 'grey.200', borderRadius: 1 }}>
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

      <DialogActions sx={{ p: 3, gap: 1 }}>
        <Button
          onClick={handleClose}
          disabled={isSubmitting}
          startIcon={<Cancel />}
        >
          취소
        </Button>
        
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting}
          variant="contained"
          startIcon={<Send />}
        >
          {isSubmitting ? '제출 중...' : '제출'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}