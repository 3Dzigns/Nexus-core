"""JWT token validation per JWT_SPEC_v1.0.md.

Security Requirements:
- RS256 signature validation (RSA public key)
- Token expiration check
- Issuer validation
- Claims extraction and validation

Reference: JWT_SPEC_v1.0.md, FR-027
"""

import logging
from datetime import datetime
from typing import Optional

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from nexus_core.config import get_settings
from nexus_core.query.schemas import JWTClaims, Role

logger = logging.getLogger(__name__)


class JWTValidationError(Exception):
    """Raised when JWT validation fails."""

    pass


class JWTValidator:
    """Validates JWT tokens per RS256 specification.

    Uses RSA public key for signature verification.
    Never trusts client-provided claims without validation.
    """

    def __init__(self, public_key: Optional[str] = None, issuer: Optional[str] = None):
        """Initialize JWT validator.

        Args:
            public_key: RSA public key in PEM format (defaults to config)
            issuer: Expected token issuer (defaults to config)
        """
        settings = get_settings()

        self.public_key = public_key or settings.jwt_public_key
        if not self.public_key:
            # Generate test key for development if not provided
            logger.warning(
                "No JWT public key configured. Using development test key. "
                "DO NOT use in production."
            )
            self.public_key = self._generate_test_public_key()

        self.issuer = issuer or settings.jwt_issuer
        self.algorithm = settings.jwt_algorithm

        logger.info(f"JWT validator initialized (issuer: {self.issuer}, algo: {self.algorithm})")

    def validate_token(self, token: str) -> JWTClaims:
        """Validate JWT token and extract claims.

        Args:
            token: JWT token string

        Returns:
            Validated JWT claims

        Raises:
            JWTValidationError: If validation fails
        """
        try:
            # Decode and validate signature, expiration, issuer
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "require_exp": True,
                    "require_iss": True,
                },
            )

            # Validate required claims exist
            if "sub" not in payload:
                raise JWTValidationError("Missing required claim: sub")
            if "role" not in payload:
                raise JWTValidationError("Missing required claim: role")

            # Validate role value
            try:
                role = Role(payload["role"])
            except ValueError:
                raise JWTValidationError(f"Invalid role value: {payload['role']}")

            # Extract claims with defaults
            claims = JWTClaims(
                sub=payload["sub"],
                role=role,
                active_game_id=payload.get("active_game_id"),
                games_owned=payload.get("games_owned", []),
                tier=payload.get("tier", "FREE"),
                exp=payload["exp"],
                iss=payload["iss"],
            )

            logger.debug(
                f"Token validated successfully (user: {claims.sub}, role: {claims.role})"
            )

            return claims

        except ExpiredSignatureError:
            logger.warning("JWT token expired")
            raise JWTValidationError("Token expired")

        except JWTClaimsError as e:
            logger.warning(f"JWT claims validation failed: {e}")
            raise JWTValidationError(f"Invalid token claims: {e}")

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise JWTValidationError(f"Invalid token: {e}")

        except Exception as e:
            logger.error(f"Unexpected error during JWT validation: {e}")
            raise JWTValidationError(f"Token validation error: {e}")

    def _generate_test_public_key(self) -> str:
        """Generate test RSA public key for development.

        WARNING: Only for development/testing. Use real keys in production.

        Returns:
            RSA public key in PEM format
        """
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        # Extract public key
        public_key = private_key.public_key()

        # Serialize to PEM format
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        logger.warning("Generated test RSA public key for development")

        return pem.decode("utf-8")
