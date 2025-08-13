import log from 'loglevel';

// Set the level based on the environment
const isDevelopment = import.meta.env.DEV;
log.setLevel(isDevelopment ? 'info' : 'warn');

const sendLogToServer = (level: log.LogLevelDesc, message: string, meta?: any) => {
  if (isDevelopment) {
    return;
  }
  
  // Use navigator.sendBeacon for reliability if available, otherwise fallback to fetch
  const logData = JSON.stringify({ level, message, meta });
  
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/api/log', new Blob([logData], { type: 'application/json' }));
  } else {
    fetch('/api/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: logData,
      keepalive: true, // Try to ensure the request is sent even if the page is unloading
    }).catch(error => {
      // Fallback console log if the server is unreachable
      console.error('Failed to send log to server:', error);
    });
  }
};

const logger = {
  info: (message: string, meta?: any) => {
    log.info(message, meta || '');
    sendLogToServer('info', message, meta);
  },
  warn: (message: string, meta?: any) => {
    log.warn(message, meta || '');
    sendLogToServer('warn', message, meta);
  },
  error: (message: string, error?: Error, meta?: any) => {
    // Construct a meaningful log message from the error object
    const errorMessage = error instanceof Error ? `${message} - ${error.name}: ${error.message}` : message;
    const errorMeta = {
      ...(meta || {}),
      stack: error instanceof Error ? error.stack : undefined,
    };
    
    log.error(errorMessage, errorMeta);
    sendLogToServer('error', errorMessage, errorMeta);
  },
  debug: (message: string, meta?: any) => {
    log.debug(message, meta || '');
    // Debug logs are typically not sent to the server
  },
};

export default logger;
