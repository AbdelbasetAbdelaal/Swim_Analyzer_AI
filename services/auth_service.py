import hashlib
import os
import hmac
from datetime import datetime
from typing import List, Optional, Tuple
from database.database import SessionLocal, engine, Base, init_db
from database.repository import CoachRepository
from models.coach_profile import CoachProfile
from core.logger import setup_logger

logger = setup_logger(__name__)

# Try to import argon2, but fail gracefully if not installed
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, InvalidHashError
    ph = PasswordHasher()
    HAS_ARGON2 = True
except ImportError:
    ph = None
    HAS_ARGON2 = False
    logger.error("System misconfigured: argon2-cffi is required for production.")


class AuthService:
    """
    Handles secure authentication, password hashing using Argon2id (with PBKDF2 upgrade),
    and coach registration/multi-tenancy session management.
    """
    
    @staticmethod
    def hash_password(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
        """
        Hashes password using Argon2id.
        Returns: (password_hash, salt_hex)
        """
        if not HAS_ARGON2:
            raise RuntimeError("System misconfigured: argon2-cffi is required for production.")
            
        return ph.hash(password), "" # Salt is handled natively by Argon2

    @staticmethod
    def _verify_pbkdf2(password: str, stored_hash: str, salt_hex: str) -> bool:
        salt_bytes = bytes.fromhex(salt_hex)
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt_bytes,
            100000
        )
        return hmac.compare_digest(hash_bytes.hex(), stored_hash)

    @classmethod
    def register_coach(
        cls, 
        username: str, 
        password: str, 
        full_name: str = "", 
        email: str = "", 
        role: str = "coach",
        creator_principal: Optional[Any] = None,
        bootstrap_token: Optional[str] = None,
        is_bootstrap: bool = False
    ) -> Tuple[bool, str, Optional[CoachProfile]]:
        """
        Registers a new account.
        If role='admin', requires an existing admin creator_principal or valid bootstrap authorization.
        Returns: (success: bool, message: str, coach_profile: Optional[CoachProfile])
        """
        if not HAS_ARGON2:
            logger.error("Cannot register account: argon2-cffi missing.")
            return False, "System misconfigured (missing argon2).", None

        username = username.strip().lower()
        role = role.strip().lower() if role else "coach"
        if role not in {"coach", "user", "admin"}:
            return False, "Invalid account role.", None

        # P1-12: Enforce authorization boundary for admin role creation
        if role == "admin":
            is_authorized = False
            if is_bootstrap:
                is_authorized = True
            elif bootstrap_token:
                expected_token = os.getenv("SWIM_ANALYZER_BOOTSTRAP_ADMIN_TOKEN", "").strip()
                if expected_token and hmac.compare_digest(bootstrap_token.strip(), expected_token):
                    is_authorized = True
            elif creator_principal is not None:
                creator_role = getattr(creator_principal, "role", None)
                if not creator_role and isinstance(creator_principal, dict):
                    creator_role = creator_principal.get("role")
                if creator_role == "admin":
                    is_authorized = True
            
            if not is_authorized:
                logger.warning(f"Unauthorized attempt to register admin account: {username}")
                return False, "Unauthorized: Administrator privileges or valid bootstrap credentials required to create an admin account.", None

        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long.", None
            
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        # Ensure database tables exist
        init_db()
        db = SessionLocal()
        try:
            repo = CoachRepository(db)
            existing = repo.get_by_username(username)
            if existing:
                return False, f"Username '{username}' is already taken.", None
                
            pwd_hash, salt = cls.hash_password(password)
            coach = CoachProfile(
                username=username,
                password_hash=pwd_hash,
                salt=salt,
                full_name=full_name.strip() or username,
                role=role,
                email=email.strip() or None,
                created_at=datetime.now().isoformat()
            )
            
            success = repo.add(coach)
            if success:
                logger.info(f"Account registered successfully: {username} ({role})")
                return True, "Account registered successfully!", coach
            else:
                return False, "Failed to save account to database.", None
        finally:
            db.close()

    @classmethod
    def login(cls, username: str, password: str) -> Tuple[bool, str, Optional[CoachProfile]]:
        """
        Authenticates an account and transparently upgrades PBKDF2 hashes to Argon2id.
        Returns: (success: bool, message: str, coach_profile: Optional[CoachProfile])
        """
        if not HAS_ARGON2:
            logger.error("Cannot process login: argon2-cffi missing.")
            return False, "System misconfigured (missing argon2).", None
            
        username = username.strip().lower()
        init_db()
        db = SessionLocal()
        try:
            repo = CoachRepository(db)
            coach = repo.get_by_username(username)
            if not coach:
                return False, "Invalid username or password.", None
            
            is_valid = False
            needs_upgrade = False
            
            # Detect Hash format
            if coach.password_hash.startswith("$argon2"):
                if not HAS_ARGON2:
                    return False, "System misconfigured (missing argon2).", None
                try:
                    is_valid = ph.verify(coach.password_hash, password)
                    if ph.check_needs_rehash(coach.password_hash):
                        needs_upgrade = True
                except (VerifyMismatchError, InvalidHashError):
                    is_valid = False
            else:
                # PBKDF2 Hash Verification
                is_valid = cls._verify_pbkdf2(password, coach.password_hash, coach.salt)
                if is_valid:
                    needs_upgrade = True
            
            if is_valid:
                # Transparent upgrade to Argon2id
                if needs_upgrade and HAS_ARGON2:
                    new_hash, _ = cls.hash_password(password)
                    coach.password_hash = new_hash
                    coach.salt = "" # Clear old salt
                    repo.add(coach) # Add performs an upsert in repo
                    logger.info(f"Upgraded password hash for {username} to Argon2id")
                
                logger.info(f"Account logged in: {username} ({coach.role})")
                return True, "Login successful!", coach
            else:
                return False, "Invalid username or password.", None
        finally:
            db.close()

    @classmethod
    def get_all_accounts(cls) -> List[CoachProfile]:
        init_db()
        db = SessionLocal()
        try:
            repo = CoachRepository(db)
            return repo.get_all()
        finally:
            db.close()

    @classmethod
    def delete_account(cls, coach_id: str) -> bool:
        init_db()
        db = SessionLocal()
        try:
            repo = CoachRepository(db)
            return repo.delete(coach_id)
        finally:
            db.close()

    @classmethod
    def seed_default_coach(cls) -> Optional[CoachProfile]:
        """
        Seeds default demo admin and coach accounts if database is empty,
        only reading from explicitly defined environment variables.
        """
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            repo = CoachRepository(db)
            
            # Read bootstrap configuration explicitly from environment
            admin_user = os.getenv("SWIM_ANALYZER_BOOTSTRAP_ADMIN_USERNAME")
            admin_pass = os.getenv("SWIM_ANALYZER_BOOTSTRAP_ADMIN_PASSWORD")
            coach_user = os.getenv("SWIM_ANALYZER_BOOTSTRAP_COACH_USERNAME")
            coach_pass = os.getenv("SWIM_ANALYZER_BOOTSTRAP_COACH_PASSWORD")

            if admin_user and admin_pass:
                if not repo.get_by_username(admin_user):
                    cls.register_coach(admin_user, admin_pass, "System Administrator", role="admin", is_bootstrap=True)

            if coach_user and coach_pass:
                existing_coach = repo.get_by_username(coach_user)
                if not existing_coach:
                    success, msg, coach = cls.register_coach(coach_user, coach_pass, f"Coach {coach_user.capitalize()}", role="coach")
                    return coach
                return existing_coach
                
            return None
        finally:
            db.close()
