import React, { useState } from 'react'
import { Box, Tabs, Tab, Alert } from '@mui/material'
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

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Alert severity="info" sx={{ mb: 3 }}>
        Git 저장소의 변경사항을 분석하여 테스트 시나리오 엑셀 파일을 자동으로 생성합니다.
      </Alert>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="main tabs">
          <Tab 
            icon={<Rocket />} 
            label="시나리오 생성" 
            {...a11yProps(0)} 
            sx={{ minHeight: 64 }}
          />
          <Tab 
            icon={<Analytics />} 
            label="피드백 분석" 
            {...a11yProps(1)} 
            sx={{ minHeight: 64 }}
          />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <ScenarioGenerationTab />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <FeedbackAnalysisTab />
      </TabPanel>
    </Box>
  )
}