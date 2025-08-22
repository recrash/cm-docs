import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Typography,
  Box,
  Chip,
  Alert,
  CircularProgress
} from '@mui/material'
import {
  Download,
  Delete,
  Close,
  Refresh
} from '@mui/icons-material'

interface BackupFile {
  filename: string
  size: number
  created_at: string
  modified_at: string
}

interface BackupFileManagementModalProps {
  open: boolean
  onClose: () => void
}

export default function BackupFileManagementModal({ open, onClose }: BackupFileManagementModalProps) {
  const [backupFiles, setBackupFiles] = useState<BackupFile[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadBackupFiles = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch('/api/feedback/backup-files')
      if (!response.ok) {
        throw new Error('백업 파일 목록을 불러오는데 실패했습니다.')
      }
      
      const data = await response.json()
      setBackupFiles(data.files || [])
    } catch (err) {
      console.error('Failed to load backup files:', err)
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (filename: string) => {
    try {
      const response = await fetch(`/api/feedback/backup-files/${filename}/download`)
      if (!response.ok) {
        throw new Error('파일 다운로드에 실패했습니다.')
      }
      
      // 파일 다운로드 처리
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to download backup file:', err)
      alert('파일 다운로드 중 오류가 발생했습니다.')
    }
  }

  const handleDelete = async (filename: string) => {
    if (!confirm(`'${filename}' 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
      return
    }

    try {
      const response = await fetch(`/api/feedback/backup-files/${filename}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        throw new Error('파일 삭제에 실패했습니다.')
      }
      
      // 파일 목록 새로고침
      await loadBackupFiles()
      alert('파일이 성공적으로 삭제되었습니다.')
    } catch (err) {
      console.error('Failed to delete backup file:', err)
      alert('파일 삭제 중 오류가 발생했습니다.')
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString)
      return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
    }
  }

  useEffect(() => {
    if (open) {
      loadBackupFiles()
    }
  }, [open])

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="md" 
      fullWidth
      PaperProps={{
        sx: { minHeight: '500px' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            📋 백업 파일 관리
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton
              onClick={loadBackupFiles}
              disabled={loading}
              size="small"
            >
              <Refresh />
            </IconButton>
            <IconButton
              onClick={onClose}
              size="small"
            >
              <Close />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
            <CircularProgress />
          </Box>
        ) : backupFiles.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body1" color="text.secondary">
              백업 파일이 없습니다.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              피드백 데이터를 삭제하면 자동으로 백업 파일이 생성됩니다.
            </Typography>
          </Box>
        ) : (
          <>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                총 {backupFiles.length}개의 백업 파일
              </Typography>
            </Box>

            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>파일명</TableCell>
                    <TableCell align="right">크기</TableCell>
                    <TableCell align="center">생성일</TableCell>
                    <TableCell align="center">수정일</TableCell>
                    <TableCell align="center">작업</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {backupFiles.map((file) => (
                    <TableRow key={file.filename} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {file.filename}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Chip 
                          label={formatFileSize(file.size)} 
                          size="small" 
                          variant="outlined" 
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2">
                          {formatDate(file.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2">
                          {formatDate(file.modified_at)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                          <IconButton
                            size="small"
                            onClick={() => handleDownload(file.filename)}
                            title="다운로드"
                            color="primary"
                          >
                            <Download fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDelete(file.filename)}
                            title="삭제"
                            color="error"
                          >
                            <Delete fontSize="small" />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          닫기
        </Button>
      </DialogActions>
    </Dialog>
  )
}