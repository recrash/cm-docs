import React from 'react';
import ReactDOM from 'react-dom/client';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import App from './App.tsx';
import logger from './utils/logger';

// --- Global Error Handling ---
window.onerror = (message, source, lineno, colno, error) => {
  logger.error('Unhandled global error:', error, {
    message,
    source,
    lineno,
    colno,
  });
  // Prevent default browser error handling
  return true;
};

window.onunhandledrejection = (event: PromiseRejectionEvent) => {
  logger.error('Unhandled promise rejection:', event.reason, {
    type: event.type,
  });
  // Prevent default browser error handling
  event.preventDefault();
};


// Material-UI theme configuration
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>,
);
