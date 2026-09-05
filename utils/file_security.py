import os
import uuid
from pathlib import Path
from core.logger import setup_logger

logger = setup_logger(__name__)

def sanitize_and_resolve_path(user_filename: str, target_dir: str, generate_unique: bool = True) -> str:
    """
    Sanitizes a user-provided filename, optionally generates a unique server-side name,
    and constructs an absolute path, verifying it cannot escape the target directory.
    
    Args:
        user_filename: The original filename from the user (e.g. upload.mp4)
        target_dir: The intended storage directory
        generate_unique: If True, prepends a UUID to prevent collisions and enumeration
        
    Returns:
        The safe, absolute file path.
        
    Raises:
        ValueError: If path traversal is detected or filename is completely invalid.
    """
    if not user_filename:
        raise ValueError("Filename cannot be empty")
        
    # 1. Sanitize the filename to strip directory paths entirely
    safe_basename = os.path.basename(user_filename.replace("\\", "/"))
    if not safe_basename or safe_basename in {".", ".."}:
        raise ValueError("Invalid filename")
        
    # 2. Generate a unique server-side filename
    if generate_unique:
        ext = os.path.splitext(safe_basename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
    else:
        unique_name = safe_basename
        
    # 3. Construct target path inside the configured storage directory
    target_path = Path(target_dir).resolve()
    
    # 4. Resolve the absolute path of the new file
    final_path = (target_path / unique_name).resolve()
    
    # 5. Verify that the resolved path is strictly inside the allowed storage directory
    try:
        final_path.relative_to(target_path)
    except ValueError:
        logger.error(f"Path traversal attempt detected: {user_filename}")
        raise ValueError("Security violation: Target path escapes allowed directory.")
        
    return str(final_path)

def verify_file_ownership(file_path: str, coach_id: str, file_owner_id: str) -> bool:
    """
    Verifies that the current coach owns the file they are trying to access.
    """
    if not coach_id or not file_owner_id:
        return False
    return str(coach_id) == str(file_owner_id)
