import log from 'loglevel';

// Set the level based on the environment
const isDevelopment = import.meta.env.DEV;
log.setLevel(isDevelopment ? 'info' : 'warn');

const sendLogToServer = (level: log.LogLevelDesc, message: string, meta?: Record<string, unknown>) => {
  if (isDevelopment) {
    return;
  }
  
  // Use navigator.sendBeacon for reliability if available, otherwise fallback to fetch
  const logData = JSON.stringify({ level, message, meta });
  
  if (navigator.sendBeacon) {
    navigator.sendBeacon(`${import.meta.env.BASE_URL}api/log`, new Blob([logData], { type: 'application/json' }));
  } else {
    fetch(`${import.meta.env.BASE_URL}api/log`, {
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
  info: (message: string, meta?: Record<string, unknown>) => {
    log.info(message, meta || '');
    sendLogToServer('info', message, meta);
  },
  warn: (message: string, meta?: Record<string, unknown>) => {
    log.warn(message, meta || '');
    sendLogToServer('warn', message, meta);
  },
  error: (message: string, error?: Error, meta?: Record<string, unknown>) => {
    // Construct a meaningful log message from the error object
    const errorMessage = error instanceof Error ? `${message} - ${error.name}: ${error.message}` : message;
    const errorMeta = {
      ...(meta || {}),
      stack: error instanceof Error ? error.stack : undefined,
    };
    
    log.error(errorMessage, errorMeta);
    sendLogToServer('error', errorMessage, errorMeta);
  },
  debug: (message: string, meta?: Record<string, unknown>) => {
    log.debug(message, meta || '');
    // Debug logs are typically not sent to the server
  },
};

export default logger;
