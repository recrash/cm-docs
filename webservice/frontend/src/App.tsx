import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Container, AppBar, Toolbar, Typography, Box, CssBaseline } from '@mui/material'
import { ThemeProvider } from '@mui/material/styles'
import { SmartToy as RobotIcon } from '@mui/icons-material'
import MainPage from './pages/MainPage'
import customTheme from './theme'

function App() {
  return (
    <ThemeProvider theme={customTheme}>
      <CssBaseline />
      <Router>
        <Box sx={{ flexGrow: 1, minHeight: '100vh', backgroundColor: 'background.default' }}>
          <AppBar 
            position="static" 
            elevation={0}
            sx={{ 
              background: 'linear-gradient(135deg, #2196f3 0%, #1976d2 100%)',
              backdropFilter: 'blur(10px)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
            }}
          >
            <Toolbar sx={{ py: 1 }}>
              <RobotIcon sx={{ mr: 2, fontSize: 32 }} />
              <Typography 
                variant="h5" 
                component="div" 
                sx={{ 
                  flexGrow: 1,
                  fontWeight: 700,
                  background: 'linear-gradient(45deg, #ffffff 30%, #e3f2fd 90%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  textShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}
              >
                🤖 테스트 시나리오 자동 생성기
              </Typography>
            </Toolbar>
          </AppBar>
          
          <Container 
            maxWidth="lg" 
            sx={{ 
              mt: 4, 
              mb: 4,
              px: { xs: 2, sm: 3, md: 4 }
            }}
          >
            <Routes>
              <Route path="/" element={<MainPage />} />
            </Routes>
          </Container>
        </Box>
      </Router>
    </ThemeProvider>
  )
}

export default App