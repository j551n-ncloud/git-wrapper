#!/usr/bin/env python3
"""
Safe File Operations - Atomic file operations with locking and error recovery

This module provides utilities for safe file operations including:
- Atomic file writes to prevent corruption
- File locking to prevent concurrent access
- Automatic backup and recovery mechanisms
- Race condition prevention
"""

import os
import json
import tempfile
import shutil
import fcntl
import time
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union, Callable
from contextlib import contextmanager


class FileLockError(Exception):
    """Exception raised when file locking fails."""
    pass


class FileOperationError(Exception):
    """Exception raised when file operations fail."""
    pass


class SafeFileOperations:
    """
    Utility class for safe file operations with atomic writes and locking.
    
    Provides methods for safely reading and writing files with protection
    against corruption, race conditions, and concurrent access issues.
    """
    
    def __init__(self, error_handler=None):
        """
        Initialize SafeFileOperations.
        
        Args:
            error_handler: Optional error handler for logging
        """
        self.error_handler = error_handler
        self._locks = {}  # Track file locks
        self._lock_mutex = threading.Lock()
    
    @contextmanager
    def file_lock(self, file_path: Union[str, Path], timeout: float = 10.0):
        """
        Context manager for file locking.
        
        Args:
            file_path: Path to the file to lock
            timeout: Maximum time to wait for lock acquisition
            
        Yields:
            File lock context
            
        Raises:
            FileLockError: If lock cannot be acquired
        """
        file_path = Path(file_path)
        lock_file = file_path.with_suffix(file_path.suffix + '.lock')
        
        # Ensure parent directory exists
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        lock_fd = None
        start_time = time.time()
        
        try:
            while True:
                try:
                    # Try to create and lock the lock file
                    lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    
                    # Try to acquire exclusive lock (Unix-like systems)
                    if hasattr(fcntl, 'LOCK_EX'):
                        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    
                    # Write PID to lock file for debugging
                    os.write(lock_fd, str(os.getpid()).encode())
                    break
                    
                except (OSError, IOError):
                    # Lock file exists or locking failed
                    if lock_fd is not None:
                        try:
                            os.close(lock_fd)
                        except:
                            pass
                        lock_fd = None
                    
                    # Check timeout
                    if time.time() - start_time > timeout:
                        raise FileLockError(f"Could not acquire lock for {file_path} within {timeout} seconds")
                    
                    # Wait briefly before retrying
                    time.sleep(0.1)
            
            # Track the lock
            with self._lock_mutex:
                self._locks[str(file_path)] = (lock_fd, lock_file)
            
            yield
            
        finally:
            # Release the lock
            with self._lock_mutex:
                if str(file_path) in self._locks:
                    del self._locks[str(file_path)]
            
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except:
                    pass
            
            # Remove lock file
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except:
                pass
    
    def atomic_write_text(self, file_path: Union[str, Path], content: str, 
                         encoding: str = 'utf-8', backup: bool = True) -> bool:
        """
        Atomically write text content to a file.
        
        Args:
            file_path: Path to the file to write
            content: Text content to write
            encoding: Text encoding to use
            backup: Whether to create a backup of existing file
            
        Returns:
            True if successful, False otherwise
        """
        file_path = Path(file_path)
        
        try:
            with self.file_lock(file_path):
                return self._atomic_write_text_locked(file_path, content, encoding, backup)
        except FileLockError as e:
            if self.error_handler:
                self.error_handler.log_error(f"File lock error: {str(e)}")
            return False
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error(f"Atomic write error: {str(e)}")
            return False
    
    def _atomic_write_text_locked(self, file_path: Path, content: str, 
                                 encoding: str, backup: bool) -> bool:
        """
        Internal method for atomic text writing (assumes file is locked).
        
        Args:
            file_path: Path to the file to write
            content: Text content to write
            encoding: Text encoding to use
            backup: Whether to create a backup of existing file
            
        Returns:
            True if successful, False otherwise
        """
        # Create backup if requested and file exists
        backup_path = None
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            try:
                shutil.copy2(file_path, backup_path)
            except Exception as e:
                if self.error_handler:
                    self.error_handler.log_warning(f"Could not create backup: {str(e)}")
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary file in the same directory
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding=encoding,
                dir=file_path.parent,
                prefix=f'.{file_path.name}_',
                suffix='.tmp',
                delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(content)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Force write to disk
            
            # Atomically replace the original file
            if os.name == 'nt':  # Windows
                if file_path.exists():
                    file_path.unlink()
            
            temp_path.replace(file_path)
            
            # Verify the write
            if not self._verify_file_content(file_path, content, encoding):
                raise FileOperationError("File content verification failed")
            
            return True
            
        except Exception as e:
            # Clean up temporary file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            
            # Try to restore from backup
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, file_path)
                    if self.error_handler:
                        self.error_handler.log_info("File restored from backup after write failure")
                except Exception as restore_error:
                    if self.error_handler:
                        self.error_handler.log_error(f"Failed to restore from backup: {str(restore_error)}")
            
            if self.error_handler:
                self.error_handler.log_error(f"Atomic write failed: {str(e)}")
            return False
    
    def atomic_write_json(self, file_path: Union[str, Path], data: Any, 
                         indent: int = 2, backup: bool = True) -> bool:
        """
        Atomically write JSON data to a file.
        
        Args:
            file_path: Path to the file to write
            data: Data to serialize as JSON
            indent: JSON indentation level
            backup: Whether to create a backup of existing file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_content = json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)
            return self.atomic_write_text(file_path, json_content, backup=backup)
        except (TypeError, ValueError) as e:
            if self.error_handler:
                self.error_handler.log_error(f"JSON serialization error: {str(e)}")
            return False
    
    def safe_read_text(self, file_path: Union[str, Path], 
                      encoding: str = 'utf-8', default: Optional[str] = None) -> Optional[str]:
        """
        Safely read text content from a file.
        
        Args:
            file_path: Path to the file to read
            encoding: Text encoding to use
            default: Default value to return if file doesn't exist or can't be read
            
        Returns:
            File content as string, or default value if reading fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return default
        
        try:
            with self.file_lock(file_path, timeout=5.0):
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
        except FileLockError:
            # If we can't get a lock, try reading without lock (read-only)
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except Exception as e:
                if self.error_handler:
                    self.error_handler.log_error(f"Failed to read file {file_path}: {str(e)}")
                return default
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error(f"Failed to read file {file_path}: {str(e)}")
            return default
    
    def safe_read_json(self, file_path: Union[str, Path], 
                      default: Optional[Any] = None) -> Optional[Any]:
        """
        Safely read JSON data from a file.
        
        Args:
            file_path: Path to the file to read
            default: Default value to return if file doesn't exist or can't be read
            
        Returns:
            Parsed JSON data, or default value if reading fails
        """
        content = self.safe_read_text(file_path)
        
        if content is None:
            return default
        
        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            if self.error_handler:
                self.error_handler.log_error(f"JSON parsing error for {file_path}: {str(e)}")
            
            # Try to restore from backup
            backup_path = Path(file_path).with_suffix(Path(file_path).suffix + '.backup')
            if backup_path.exists():
                try:
                    backup_content = self.safe_read_text(backup_path)
                    if backup_content:
                        backup_data = json.loads(backup_content)
                        if self.error_handler:
                            self.error_handler.log_info(f"Restored JSON data from backup for {file_path}")
                        return backup_data
                except Exception as backup_error:
                    if self.error_handler:
                        self.error_handler.log_error(f"Failed to restore from backup: {str(backup_error)}")
            
            return default
    
    def _verify_file_content(self, file_path: Path, expected_content: str, 
                           encoding: str) -> bool:
        """
        Verify that file content matches expected content.
        
        Args:
            file_path: Path to the file to verify
            expected_content: Expected file content
            encoding: Text encoding to use
            
        Returns:
            True if content matches, False otherwise
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                actual_content = f.read()
            return actual_content == expected_content
        except Exception:
            return False
    
    def cleanup_old_backups(self, file_path: Union[str, Path], 
                           max_backups: int = 5) -> None:
        """
        Clean up old backup files, keeping only the most recent ones.
        
        Args:
            file_path: Path to the main file
            max_backups: Maximum number of backup files to keep
        """
        file_path = Path(file_path)
        backup_pattern = f"{file_path.name}.backup*"
        
        try:
            # Find all backup files
            backup_files = list(file_path.parent.glob(backup_pattern))
            
            if len(backup_files) <= max_backups:
                return
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Remove old backups
            for old_backup in backup_files[max_backups:]:
                try:
                    old_backup.unlink()
                    if self.error_handler:
                        self.error_handler.log_debug(f"Removed old backup: {old_backup}")
                except Exception as e:
                    if self.error_handler:
                        self.error_handler.log_warning(f"Failed to remove old backup {old_backup}: {str(e)}")
        
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error(f"Failed to cleanup old backups: {str(e)}")
    
    def get_file_info(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information, or None if file doesn't exist
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return None
        
        try:
            stat = file_path.stat()
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'permissions': oct(stat.st_mode)[-3:],
                'is_readable': os.access(file_path, os.R_OK),
                'is_writable': os.access(file_path, os.W_OK),
            }
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error(f"Failed to get file info for {file_path}: {str(e)}")
            return None


# Convenience functions for common operations
def safe_write_json(file_path: Union[str, Path], data: Any, 
                   error_handler=None, **kwargs) -> bool:
    """
    Convenience function for safely writing JSON data.
    
    Args:
        file_path: Path to the file to write
        data: Data to serialize as JSON
        error_handler: Optional error handler
        **kwargs: Additional arguments for atomic_write_json
        
    Returns:
        True if successful, False otherwise
    """
    safe_ops = SafeFileOperations(error_handler)
    return safe_ops.atomic_write_json(file_path, data, **kwargs)


def safe_read_json(file_path: Union[str, Path], default: Optional[Any] = None,
                  error_handler=None) -> Optional[Any]:
    """
    Convenience function for safely reading JSON data.
    
    Args:
        file_path: Path to the file to read
        default: Default value to return if reading fails
        error_handler: Optional error handler
        
    Returns:
        Parsed JSON data, or default value if reading fails
    """
    safe_ops = SafeFileOperations(error_handler)
    return safe_ops.safe_read_json(file_path, default)


def safe_write_text(file_path: Union[str, Path], content: str,
                   error_handler=None, **kwargs) -> bool:
    """
    Convenience function for safely writing text content.
    
    Args:
        file_path: Path to the file to write
        content: Text content to write
        error_handler: Optional error handler
        **kwargs: Additional arguments for atomic_write_text
        
    Returns:
        True if successful, False otherwise
    """
    safe_ops = SafeFileOperations(error_handler)
    return safe_ops.atomic_write_text(file_path, content, **kwargs)


def safe_read_text(file_path: Union[str, Path], default: Optional[str] = None,
                  error_handler=None, **kwargs) -> Optional[str]:
    """
    Convenience function for safely reading text content.
    
    Args:
        file_path: Path to the file to read
        default: Default value to return if reading fails
        error_handler: Optional error handler
        **kwargs: Additional arguments for safe_read_text
        
    Returns:
        File content as string, or default value if reading fails
    """
    safe_ops = SafeFileOperations(error_handler)
    return safe_ops.safe_read_text(file_path, default, **kwargs)