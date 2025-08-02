import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Container, AppBar, Toolbar, Typography, Box } from '@mui/material'
import { SmartToy as RobotIcon } from '@mui/icons-material'
import MainPage from './pages/MainPage'

function App() {
  return (
    <Router>
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <RobotIcon sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              🤖 테스트 시나리오 자동 생성기
            </Typography>
          </Toolbar>
        </AppBar>
        
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/" element={<MainPage />} />
          </Routes>
        </Container>
      </Box>
    </Router>
  )
}

export default App