from datetime import datetime
import logging
import os


class LoggingMixin:
    """Mixin class that adds enhanced print functionality with logging"""

    def __init__(self, log_file=None, log_dir="logs", *args, **kwargs):
        super().__init__(*args, **kwargs)  # Call parent __init__ if exists

        # Create timestamp for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create class-specific subdirectory within logs
        class_name = self.__class__.__name__.lower()
        class_log_dir = os.path.join(log_dir, class_name)

        # Create directories if they don't exist
        if not os.path.exists(class_log_dir):
            os.makedirs(class_log_dir)

        # Generate timestamped log file name
        if log_file is None:
            log_filename = f"{class_name}_{timestamp}.log"
        else:
            # Add timestamp to custom filename
            name, ext = os.path.splitext(log_file)
            log_filename = f"{name}_{timestamp}{ext}"

        # Combine directory and filename
        self.log_file = os.path.join(class_log_dir, log_filename)
        self._setup_logger()

    def _setup_logger(self):
        """Set up the logger configuration"""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.setLevel(logging.INFO)

        # Create file handler if not already exists
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def print(self, *args, sep=" ", end="\n", file=None, flush=False):
        """Enhanced print that also logs to file"""
        # Convert all arguments to strings and join them
        message = sep.join(str(arg) for arg in args)

        # Print to console (standard behavior)
        print(*args, sep=sep, end=end, file=file, flush=flush)

        # Log to file
        self.logger.info(message)

    def print_debug(self, *args, sep=" "):
        """Print and log as debug level"""
        message = sep.join(str(arg) for arg in args)
        print(f"[DEBUG] {message}")
        self.logger.debug(message)

    def print_error(self, *args, sep=" "):
        """Print and log as error level"""
        message = sep.join(str(arg) for arg in args)
        print(f"[ERROR] {message}")
        self.logger.error(message)
