import time
from functools import wraps

def retry(max_attempts: int = 3, delay: float = 2.0, exceptions=(Exception,)):
    """Decorator that retries a function on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_attempts:
                        wait = delay * attempt  # exponential backoff
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}). "
                            f"Retrying in {wait}s... Error: {e}"
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts"
                        )
            raise last_error
        return wrapper
    return decorator

class PipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass

class ScriptGenerationError(PipelineError):
    """Raised when the LLM fails to generate a script."""
    pass

class VoiceGenerationError(PipelineError):
    """Raised when ElevenLabs voice generation fails."""
    pass

class VideoRenderError(PipelineError):
    """Raised when Remotion render fails."""
    pass

class UploadError(PipelineError):
    """Raised when YouTube upload fails."""
    pass

class ConfigError(PipelineError):
    """Raised when configuration is invalid."""
    pass

class QuotaExceededError(PipelineError):
    """Raised when an API quota is exceeded."""
    pass