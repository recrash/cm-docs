import React, { useState } from 'react'
import { Box, Tabs, Tab, Alert, Typography } from '@mui/material'
import { Rocket, Analytics } from '@mui/icons-material'
import ScenarioGenerationTab from '../components/ScenarioGenerationTab'
import FeedbackAnalysisTab from '../components/FeedbackAnalysisTab'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`main-tabpanel-${index}`}
      aria-labelledby={`main-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

function a11yProps(index: number) {
  return {
    id: `main-tab-${index}`,
    'aria-controls': `main-tabpanel-${index}`,
  }
}

export default function MainPage() {
  const [tabValue, setTabValue] = useState(0)

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Alert 
        severity="info" 
        sx={{ 
          mb: 4,
          borderRadius: 3,
          border: '2px solid rgba(33, 150, 243, 0.2)',
          background: 'linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%)',
          '& .MuiAlert-icon': {
            fontSize: '1.5rem'
          }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Typography variant="body1" sx={{ fontWeight: 500 }}>
            🚀 Git 저장소의 변경사항을 분석하여 테스트 시나리오 엑셀 파일을 자동으로 생성합니다.
          </Typography>
        </Box>
      </Alert>

      <Box 
        sx={{ 
          borderBottom: 2, 
          borderColor: 'rgba(33, 150, 243, 0.1)',
          background: 'linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%)',
          borderRadius: '16px 16px 0 0',
          overflow: 'hidden'
        }}
      >
        <Tabs 
          value={tabValue} 
          onChange={handleTabChange} 
          aria-label="main tabs"
          sx={{
            '& .MuiTab-root': {
              minHeight: 72,
              fontSize: '1rem',
              fontWeight: 600,
              textTransform: 'none',
              px: { xs: 2, sm: 4 },
              '&.Mui-selected': {
                background: 'linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%)',
                color: 'primary.main'
              }
            },
            '& .MuiTabs-indicator': {
              height: 4,
              borderRadius: '4px 4px 0 0',
              background: 'linear-gradient(90deg, #2196f3 0%, #1976d2 100%)'
            }
          }}
        >
          <Tab 
            icon={<Rocket sx={{ fontSize: 28 }} />} 
            label="시나리오 생성" 
            {...a11yProps(0)} 
            sx={{ 
              flexDirection: { xs: 'column', sm: 'row' },
              gap: { xs: 1, sm: 2 }
            }}
          />
          <Tab 
            icon={<Analytics sx={{ fontSize: 28 }} />} 
            label="피드백 분석" 
            {...a11yProps(1)} 
            sx={{ 
              flexDirection: { xs: 'column', sm: 'row' },
              gap: { xs: 1, sm: 2 }
            }}
          />
        </Tabs>
      </Box>

      <Box 
        sx={{ 
          background: 'linear-gradient(180deg, #f8f9ff 0%, #ffffff 100%)',
          borderRadius: '0 0 16px 16px',
          minHeight: '60vh'
        }}
      >
        <TabPanel value={tabValue} index={0}>
          <ScenarioGenerationTab />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <FeedbackAnalysisTab />
        </TabPanel>
      </Box>
    </Box>
  )
}