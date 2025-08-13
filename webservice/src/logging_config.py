import logging
import sys
import os
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import datetime

class DatedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Custom handler to create log files with date at the beginning of the filename.
    e.g., 20250803_backend.log
    """
    def __init__(self, filename_prefix, when='midnight', backupCount=0, encoding=None, delay=False, utc=False, atTime=None):
        self.prefix = filename_prefix
        # Correctly determine project root and logs directory
        self.log_dir = Path(__file__).resolve().parents[1] / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Construct the initial filename
        current_date = datetime.date.today().strftime('%Y%m%d')
        filename = self.log_dir / f"{current_date}_{self.prefix}.log"
        
        super().__init__(str(filename), when, 1, backupCount, encoding, delay, utc, atTime)

    def doRollover(self):
        """
        Overwrites the rollover method to use the new date in the filename.
        """
        self.stream.close()
        # get the time that this sequence started at and make it a TimeTuple
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
        
        # New filename based on the new date
        dfn = str(self.log_dir / f"{time.strftime('%Y%m%d', timeTuple)}_{self.prefix}.log")

        if os.path.exists(dfn):
            os.remove(dfn)

        self.baseFilename = dfn
        
        # Open new log file
        self.stream = self._open()
        
        # Cleanup old logs
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)

def setup_logging():
    """
    Sets up the logging configuration for the entire application.
    """
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(exist_ok=True)

    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    formatter = logging.Formatter(log_format)

    # --- Handlers ---
    backend_handler = DatedRotatingFileHandler("backend", backupCount=7)
    frontend_handler = DatedRotatingFileHandler("frontend", backupCount=7)
    
    backend_handler.setFormatter(formatter)
    frontend_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # --- Configure Loggers ---
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(backend_handler)
        root_logger.addHandler(console_handler)

    frontend_logger = logging.getLogger("frontend")
    if not frontend_logger.handlers:
        frontend_logger.setLevel(logging.INFO)
        frontend_logger.propagate = False
        frontend_logger.addHandler(frontend_handler)
        frontend_logger.addHandler(console_handler)

    # Use a generic logger for the initial message to avoid duplicate setup logs
    initial_logger = logging.getLogger(__name__)
    initial_logger.info("Logging configured with date-prefixed file names.")
