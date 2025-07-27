"""
Security Tests
==============

Comprehensive security testing for the DSL to PNG conversion system,
including input validation, authentication, authorization, injection attacks,
and security vulnerability detection.
"""

import pytest
import asyncio
import json
import hashlib
import base64
import time
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
import jwt
from pathlib import Path
import tempfile
import os

from src.core.dsl.parser import DSLParser
from src.core.rendering.html_generator import HTMLGenerator
from src.core.rendering.png_generator import PNGGenerator
from src.core.storage.manager import FileStorageManager
from src.models.schemas import RenderOptions

from tests.utils.data_generators import MockDataGenerator
from tests.utils.helpers import create_temp_directory


class TestInputValidationSecurity:
    """Test security aspects of input validation."""

    @pytest.fixture
    def dsl_parser(self):
        """Create DSL parser for testing."""
        return DSLParser()

    def test_malicious_json_injection(self, dsl_parser):
        """Test protection against JSON injection attacks."""
        malicious_payloads = [
            # Script injection attempts
            {
                "title": "<script>alert('xss')</script>",
                "viewport": {"width": 800, "height": 600},
                "elements": [{"type": "text", "content": "test"}],
            },
            # SQL injection patterns (even though we don't use SQL directly)
            {
                "title": "'; DROP TABLE users; --",
                "viewport": {"width": 800, "height": 600},
                "elements": [{"type": "text", "content": "test"}],
            },
            # Command injection attempts
            {
                "title": "test && rm -rf /",
                "viewport": {"width": 800, "height": 600},
                "elements": [{"type": "text", "content": "test"}],
            },
            # Path traversal attempts
            {
                "title": "../../../etc/passwd",
                "viewport": {"width": 800, "height": 600},
                "elements": [{"type": "text", "content": "test"}],
            },
            # Large payload attack
            {
                "title": "A" * 10000,  # Very large title
                "viewport": {"width": 800, "height": 600},
                "elements": [{"type": "text", "content": "test"}],
            },
        ]

        for payload in malicious_payloads:
            try:
                document = dsl_parser.parse_dict(payload)
                # If parsing succeeds, verify content is sanitized
                if document:
                    # Check that dangerous content is escaped or removed
                    assert "<script>" not in str(document.title)
                    assert "DROP TABLE" not in str(document.title)
                    assert "rm -rf" not in str(document.title)
                    assert len(str(document.title)) <= 1000  # Reasonable length limit
            except Exception as e:
                # Parser should reject malicious input gracefully
                assert "validation error" in str(e).lower() or "invalid" in str(e).lower()

    def test_malformed_dsl_structures(self, dsl_parser):
        """Test handling of malformed DSL structures."""
        malformed_payloads = [
            # Missing required fields
            {"viewport": {"width": 800, "height": 600}},  # Missing title
            {"title": "test"},  # Missing viewport
            # Invalid data types
            {
                "title": 12345,  # Should be string
                "viewport": {"width": 800, "height": 600},
                "elements": [],
            },
            {"title": "test", "viewport": "invalid", "elements": []},  # Should be object
            # Circular references (if using object references)
            {
                "title": "test",
                "viewport": {"width": 800, "height": 600},
                "elements": [{"type": "ref", "target": "self"}],
            },
            # Extremely nested structures
            {
                "title": "test",
                "viewport": {"width": 800, "height": 600},
                "elements": self._create_deeply_nested_elements(50),
            },
        ]

        for payload in malformed_payloads:
            with pytest.raises((ValueError, TypeError, KeyError)):
                dsl_parser.parse_dict(payload)

    def test_oversized_input_protection(self, dsl_parser):
        """Test protection against oversized input attacks."""
        # Test large number of elements
        large_payload = {
            "title": "Large Payload Test",
            "viewport": {"width": 800, "height": 600},
            "elements": [
                {"type": "text", "content": f"Element {i}"}
                for i in range(10000)  # Very large number of elements
            ],
        }

        # Parser should either handle gracefully or reject
        try:
            document = dsl_parser.parse_dict(large_payload)
            if document:
                # Should have reasonable limits on elements
                assert len(document.elements) <= 1000
        except Exception as e:
            assert "too large" in str(e).lower() or "limit exceeded" in str(e).lower()

        # Test oversized content
        oversized_content = {
            "title": "Oversized Content Test",
            "viewport": {"width": 800, "height": 600},
            "elements": [{"type": "text", "content": "X" * 1000000}],  # 1MB of text
        }

        try:
            document = dsl_parser.parse_dict(oversized_content)
            if document:
                # Content should be truncated or limited
                for element in document.elements:
                    assert len(str(element.content)) <= 100000  # Reasonable limit
        except Exception as e:
            assert "too large" in str(e).lower() or "size limit" in str(e).lower()

    def _create_deeply_nested_elements(self, depth):
        """Create deeply nested element structure for testing."""
        if depth <= 0:
            return [{"type": "text", "content": "deep"}]

        return [{"type": "container", "children": self._create_deeply_nested_elements(depth - 1)}]


class TestHTMLInjectionSecurity:
    """Test protection against HTML injection attacks."""

    @pytest.fixture
    async def html_generator(self):
        """Create HTML generator for testing."""
        return HTMLGenerator()

    @pytest.mark.asyncio
    async def test_script_injection_prevention(self, html_generator):
        """Test prevention of script injection in generated HTML."""
        malicious_dsl = {
            "title": "XSS Test",
            "viewport": {"width": 800, "height": 600},
            "elements": [
                {"type": "text", "content": "<script>alert('xss')</script>Malicious content"},
                {
                    "type": "text",
                    "content": "javascript:alert('xss')",
                    "style": {"cursor": "pointer"},
                },
                {"type": "html", "content": "<img src='x' onerror='alert(1)'>"},
            ],
        }

        document = MockDataGenerator.create_mock_document(malicious_dsl)
        render_options = RenderOptions(width=800, height=600)

        html = await html_generator.generate_html(document, render_options)

        # Verify script tags are escaped or removed
        assert "<script>" not in html
        assert "javascript:" not in html
        assert "onerror=" not in html
        assert "onload=" not in html
        assert "onclick=" not in html

        # Verify content is properly escaped
        assert "&lt;script&gt;" in html or "alert" not in html

    @pytest.mark.asyncio
    async def test_css_injection_prevention(self, html_generator):
        """Test prevention of CSS injection attacks."""
        malicious_css_dsl = {
            "title": "CSS Injection Test",
            "viewport": {"width": 800, "height": 600},
            "elements": [
                {
                    "type": "text",
                    "content": "Test content",
                    "style": {
                        "background": "url('javascript:alert(1)')",
                        "expression": "alert('xss')",  # IE expression
                        "behavior": "url(malicious.htc)",  # IE behavior
                    },
                }
            ],
        }

        document = MockDataGenerator.create_mock_document(malicious_css_dsl)
        render_options = RenderOptions(width=800, height=600)

        html = await html_generator.generate_html(document, render_options)

        # Verify dangerous CSS is removed or escaped
        assert "javascript:" not in html
        assert "expression(" not in html
        assert "behavior:" not in html
        assert "@import" not in html  # Prevent CSS imports

    @pytest.mark.asyncio
    async def test_url_injection_prevention(self, html_generator):
        """Test prevention of malicious URL injection."""
        malicious_url_dsl = {
            "title": "URL Injection Test",
            "viewport": {"width": 800, "height": 600},
            "elements": [
                {"type": "link", "content": "Click me", "href": "javascript:alert('xss')"},
                {"type": "image", "src": "data:text/html,<script>alert('xss')</script>"},
                {
                    "type": "link",
                    "content": "External",
                    "href": "http://evil.com/steal?data=sensitive",
                },
            ],
        }

        document = MockDataGenerator.create_mock_document(malicious_url_dsl)
        render_options = RenderOptions(width=800, height=600)

        html = await html_generator.generate_html(document, render_options)

        # Verify dangerous URLs are blocked or sanitized
        assert "javascript:" not in html
        assert "data:text/html" not in html
        # External URLs should be either blocked or have security attributes
        if "evil.com" in html:
            assert 'rel="noopener noreferrer"' in html


class TestAuthenticationSecurity:
    """Test authentication and authorization security."""

    @pytest.fixture
    def mock_auth_settings(self):
        """Mock authentication settings."""
        with patch("src.config.settings.get_settings") as mock_settings:
            settings = Mock()
            settings.jwt_secret = "test-secret-key-for-testing-only"
            settings.jwt_algorithm = "HS256"
            settings.jwt_expiration = 3600
            settings.require_authentication = True
            mock_settings.return_value = settings
            yield settings

    def test_jwt_token_validation(self, mock_auth_settings):
        """Test JWT token validation security."""
        # Test valid token
        valid_payload = {
            "user_id": "test-user",
            "permissions": ["render"],
            "exp": int(time.time()) + 3600,
        }
        valid_token = jwt.encode(
            valid_payload, mock_auth_settings.jwt_secret, algorithm=mock_auth_settings.jwt_algorithm
        )

        # Verify valid token is accepted
        decoded = jwt.decode(
            valid_token,
            mock_auth_settings.jwt_secret,
            algorithms=[mock_auth_settings.jwt_algorithm],
        )
        assert decoded["user_id"] == "test-user"

        # Test expired token
        expired_payload = {
            "user_id": "test-user",
            "permissions": ["render"],
            "exp": int(time.time()) - 3600,  # Expired
        }
        expired_token = jwt.encode(
            expired_payload,
            mock_auth_settings.jwt_secret,
            algorithm=mock_auth_settings.jwt_algorithm,
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                expired_token,
                mock_auth_settings.jwt_secret,
                algorithms=[mock_auth_settings.jwt_algorithm],
            )

        # Test tampered token
        tampered_token = valid_token[:-10] + "tampered123"
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                tampered_token,
                mock_auth_settings.jwt_secret,
                algorithms=[mock_auth_settings.jwt_algorithm],
            )

    def test_permission_validation(self, mock_auth_settings):
        """Test permission-based access control."""
        # Token with limited permissions
        limited_payload = {
            "user_id": "limited-user",
            "permissions": ["read"],  # No render permission
            "exp": int(time.time()) + 3600,
        }
        limited_token = jwt.encode(
            limited_payload,
            mock_auth_settings.jwt_secret,
            algorithm=mock_auth_settings.jwt_algorithm,
        )

        decoded = jwt.decode(
            limited_token,
            mock_auth_settings.jwt_secret,
            algorithms=[mock_auth_settings.jwt_algorithm],
        )

        # Verify permission checking
        assert "render" not in decoded.get("permissions", [])
        assert "read" in decoded.get("permissions", [])

        # Test admin permissions
        admin_payload = {
            "user_id": "admin-user",
            "permissions": ["render", "admin", "delete"],
            "exp": int(time.time()) + 3600,
        }
        admin_token = jwt.encode(
            admin_payload, mock_auth_settings.jwt_secret, algorithm=mock_auth_settings.jwt_algorithm
        )

        admin_decoded = jwt.decode(
            admin_token,
            mock_auth_settings.jwt_secret,
            algorithms=[mock_auth_settings.jwt_algorithm],
        )

        assert "admin" in admin_decoded.get("permissions", [])

    def test_rate_limiting_security(self):
        """Test rate limiting protection."""
        from collections import defaultdict
        import time

        # Simulate rate limiting logic
        request_counts = defaultdict(list)
        rate_limit = 10  # 10 requests per minute
        time_window = 60  # 60 seconds

        def check_rate_limit(client_ip):
            """Check if client is within rate limits."""
            now = time.time()
            # Clean old requests
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip] if now - req_time < time_window
            ]

            if len(request_counts[client_ip]) >= rate_limit:
                return False

            request_counts[client_ip].append(now)
            return True

        # Test normal usage
        client_ip = "192.168.1.100"
        for _ in range(rate_limit):
            assert check_rate_limit(client_ip)

        # Test rate limit exceeded
        assert not check_rate_limit(client_ip)

        # Test different client
        other_client = "192.168.1.101"
        assert check_rate_limit(other_client)


class TestFileSystemSecurity:
    """Test file system security and path traversal prevention."""

    @pytest.fixture
    async def storage_manager(self):
        """Create storage manager for testing."""
        with create_temp_directory() as temp_dir:
            with patch("src.core.storage.manager.get_settings") as mock_settings:
                mock_settings.return_value.storage_path = temp_dir / "storage"
                mock_settings.return_value.cache_ttl = 3600

                manager = FileStorageManager()
                await manager.initialize()
                yield manager
                await manager.close()

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, storage_manager):
        """Test prevention of path traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "../../../../../../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",  # URL encoded
            "....//....//....//etc/passwd",  # Double dots
        ]

        for malicious_path in malicious_paths:
            # Try to use malicious path as filename
            with pytest.raises((ValueError, FileNotFoundError, PermissionError)):
                png_result = MockDataGenerator.generate_png_result()
                await storage_manager.store_png(png_result, malicious_path)

    @pytest.mark.asyncio
    async def test_file_permission_security(self, storage_manager):
        """Test file permission security."""
        png_result = MockDataGenerator.generate_png_result()
        content_hash = await storage_manager.store_png(png_result, "test-permissions")

        # Verify stored file has secure permissions
        file_path = storage_manager._get_file_path(content_hash)
        if file_path.exists():
            file_stat = file_path.stat()
            # File should not be world-readable/writable
            permissions = oct(file_stat.st_mode)[-3:]
            assert permissions[2] in ["0", "4"]  # No world write, limited read

    def test_symlink_attack_prevention(self):
        """Test prevention of symlink attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a symlink to sensitive file
            sensitive_file = temp_path / "sensitive.txt"
            sensitive_file.write_text("sensitive data")

            symlink_path = temp_path / "symlink_attack"
            symlink_path.symlink_to(sensitive_file)

            # Test that following symlinks is prevented
            def safe_read_file(filepath):
                """Safely read file without following symlinks."""
                path = Path(filepath)
                if path.is_symlink():
                    raise ValueError("Symlinks not allowed")
                return path.read_text()

            # Normal file should work
            assert safe_read_file(sensitive_file) == "sensitive data"

            # Symlink should be rejected
            with pytest.raises(ValueError, match="Symlinks not allowed"):
                safe_read_file(symlink_path)


class TestDataSanitizationSecurity:
    """Test data sanitization and output encoding."""

    def test_content_sanitization(self):
        """Test proper content sanitization."""
        import html
        import re

        dangerous_content = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "onclick='alert(1)'",
            "style='background:url(javascript:alert(1))'",
        ]

        def sanitize_content(content):
            """Sanitize content for safe display."""
            # Remove script tags
            content = re.sub(
                r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL
            )

            # Remove javascript: and vbscript: protocols
            content = re.sub(r"(javascript|vbscript):", "", content, flags=re.IGNORECASE)

            # Remove event handlers
            content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', "", content, flags=re.IGNORECASE)

            # HTML escape remaining content
            content = html.escape(content)

            return content

        for dangerous in dangerous_content:
            sanitized = sanitize_content(dangerous)

            # Verify dangerous patterns are removed or escaped
            assert "<script>" not in sanitized.lower()
            assert "javascript:" not in sanitized.lower()
            assert "onclick=" not in sanitized.lower()
            assert "alert" not in sanitized or "&" in sanitized  # Either removed or escaped

    def test_url_validation_and_sanitization(self):
        """Test URL validation and sanitization."""
        import urllib.parse

        def validate_url(url):
            """Validate and sanitize URLs."""
            if not url:
                return None

            # Parse URL
            parsed = urllib.parse.urlparse(url)

            # Reject dangerous schemes
            dangerous_schemes = ["javascript", "vbscript", "data", "file"]
            if parsed.scheme.lower() in dangerous_schemes:
                return None

            # Only allow safe schemes
            safe_schemes = ["http", "https", "mailto"]
            if parsed.scheme and parsed.scheme.lower() not in safe_schemes:
                return None

            # Reconstruct safe URL
            return urllib.parse.urlunparse(parsed)

        test_urls = [
            ("https://example.com", "https://example.com"),
            ("http://example.com", "http://example.com"),
            ("mailto:test@example.com", "mailto:test@example.com"),
            ("javascript:alert('xss')", None),
            ("vbscript:msgbox('xss')", None),
            ("data:text/html,<script>alert('xss')</script>", None),
            ("file:///etc/passwd", None),
            ("ftp://example.com", None),
        ]

        for input_url, expected in test_urls:
            result = validate_url(input_url)
            assert result == expected


class TestCryptographicSecurity:
    """Test cryptographic security aspects."""

    def test_secure_random_generation(self):
        """Test secure random number generation."""
        import secrets

        # Test token generation
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)

        assert len(token1) > 0
        assert len(token2) > 0
        assert token1 != token2  # Should be different

        # Test cryptographic random bytes
        random_bytes1 = secrets.token_bytes(32)
        random_bytes2 = secrets.token_bytes(32)

        assert len(random_bytes1) == 32
        assert len(random_bytes2) == 32
        assert random_bytes1 != random_bytes2

    def test_password_hashing_security(self):
        """Test secure password hashing."""
        import bcrypt

        password = "test_password_123"

        # Hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

        # Verify password
        assert bcrypt.checkpw(password.encode("utf-8"), hashed)

        # Verify wrong password fails
        wrong_password = "wrong_password"
        assert not bcrypt.checkpw(wrong_password.encode("utf-8"), hashed)

        # Verify salt is random
        salt2 = bcrypt.gensalt()
        hashed2 = bcrypt.hashpw(password.encode("utf-8"), salt2)
        assert hashed != hashed2  # Different salts produce different hashes

    def test_content_hash_integrity(self):
        """Test content hash integrity verification."""
        import hashlib

        def calculate_content_hash(content):
            """Calculate SHA-256 hash of content."""
            return hashlib.sha256(content.encode("utf-8")).hexdigest()

        def verify_content_integrity(content, expected_hash):
            """Verify content integrity using hash."""
            actual_hash = calculate_content_hash(content)
            return actual_hash == expected_hash

        test_content = "This is test content for integrity verification"
        content_hash = calculate_content_hash(test_content)

        # Verify correct content
        assert verify_content_integrity(test_content, content_hash)

        # Verify tampered content fails
        tampered_content = test_content + " tampered"
        assert not verify_content_integrity(tampered_content, content_hash)


class TestPrivacyAndDataProtection:
    """Test privacy and data protection measures."""

    def test_sensitive_data_sanitization(self):
        """Test sanitization of sensitive data from logs."""
        import re

        def sanitize_log_data(log_message):
            """Sanitize sensitive data from log messages."""
            # Remove potential passwords
            log_message = re.sub(
                r"(password|passwd|pwd)=\S+", r"\1=***", log_message, flags=re.IGNORECASE
            )

            # Remove potential API keys
            log_message = re.sub(
                r"(api[_-]?key|token)=\S+", r"\1=***", log_message, flags=re.IGNORECASE
            )

            # Remove potential emails (partial masking)
            log_message = re.sub(
                r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b", r"\1***@\2", log_message
            )

            # Remove potential credit card numbers
            log_message = re.sub(
                r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "XXXX-XXXX-XXXX-XXXX", log_message
            )

            return log_message

        test_logs = [
            "User login failed: password=secret123",
            "API request with api_key=sk_test_1234567890abcdef",
            "Processing request for user@example.com",
            "Payment processed: 4532-1234-5678-9012",
        ]

        expected_sanitized = [
            "User login failed: password=***",
            "API request with api_key=***",
            "Processing request for user***@example.com",
            "Payment processed: XXXX-XXXX-XXXX-XXXX",
        ]

        for log, expected in zip(test_logs, expected_sanitized):
            sanitized = sanitize_log_data(log)
            assert sanitized == expected

    def test_pii_detection_and_masking(self):
        """Test detection and masking of PII in user content."""
        import re

        def mask_pii(content):
            """Mask personally identifiable information."""
            # Mask email addresses
            content = re.sub(
                r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "[EMAIL]", content
            )

            # Mask phone numbers
            content = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]", content)

            # Mask SSN patterns
            content = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", content)

            # Mask credit card patterns
            content = re.sub(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CARD]", content)

            return content

        test_content = """
        Contact information:
        Email: user@example.com
        Phone: 555-123-4567
        SSN: 123-45-6789
        Card: 4532 1234 5678 9012
        """

        masked = mask_pii(test_content)

        assert "user@example.com" not in masked
        assert "555-123-4567" not in masked
        assert "123-45-6789" not in masked
        assert "4532 1234 5678 9012" not in masked
        assert "[EMAIL]" in masked
        assert "[PHONE]" in masked
        assert "[SSN]" in masked
        assert "[CARD]" in masked


class TestSecurityHeaders:
    """Test security headers and configurations."""

    def test_security_headers_configuration(self):
        """Test proper security headers configuration."""
        required_security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        def validate_security_headers(headers):
            """Validate that security headers are properly set."""
            missing_headers = []
            weak_headers = []

            for header, expected_value in required_security_headers.items():
                if header not in headers:
                    missing_headers.append(header)
                elif not headers[header].startswith(expected_value.split(";")[0]):
                    weak_headers.append(header)

            return missing_headers, weak_headers

        # Test with proper headers
        good_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        missing, weak = validate_security_headers(good_headers)
        assert len(missing) == 0
        assert len(weak) == 0

        # Test with missing headers
        bad_headers = {
            "X-Content-Type-Options": "nosniff",
            # Missing other security headers
        }

        missing, weak = validate_security_headers(bad_headers)
        assert len(missing) > 0

    def test_cors_configuration_security(self):
        """Test CORS configuration security."""

        def validate_cors_config(cors_config):
            """Validate CORS configuration for security."""
            issues = []

            # Check for overly permissive origins
            if cors_config.get("allow_origins") == ["*"]:
                if cors_config.get("allow_credentials", False):
                    issues.append("Cannot use wildcard origin with credentials")

            # Check for dangerous headers
            dangerous_headers = ["Authorization", "X-Api-Key", "X-Auth-Token"]
            allowed_headers = cors_config.get("allow_headers", [])
            if "*" in allowed_headers:
                issues.append("Wildcard headers can expose sensitive data")

            # Check for dangerous methods
            dangerous_methods = ["TRACE", "CONNECT"]
            allowed_methods = cors_config.get("allow_methods", [])
            for method in dangerous_methods:
                if method in allowed_methods:
                    issues.append(f"Dangerous method {method} allowed")

            return issues

        # Test secure CORS config
        secure_config = {
            "allow_origins": ["https://trusted-domain.com"],
            "allow_methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"],
            "allow_credentials": True,
        }

        issues = validate_cors_config(secure_config)
        assert len(issues) == 0

        # Test insecure CORS config
        insecure_config = {
            "allow_origins": ["*"],
            "allow_methods": ["GET", "POST", "TRACE"],
            "allow_headers": ["*"],
            "allow_credentials": True,
        }

        issues = validate_cors_config(insecure_config)
        assert len(issues) > 0


class TestSecurityCompliance:
    """Test overall security compliance and best practices."""

    def test_dependency_security_scanning(self):
        """Test that dependencies don't have known vulnerabilities."""
        # This would typically integrate with tools like safety or bandit
        # For testing purposes, we'll simulate the check

        def check_dependency_vulnerabilities(dependencies):
            """Check dependencies for known vulnerabilities."""
            # Known vulnerable packages (examples)
            vulnerable_packages = {
                "django": ["2.0.0", "2.1.0"],  # Example vulnerable versions
                "flask": ["0.12.0"],
                "requests": ["2.19.0"],
            }

            vulnerabilities = []
            for package, version in dependencies.items():
                if package in vulnerable_packages:
                    if version in vulnerable_packages[package]:
                        vulnerabilities.append(f"{package}=={version}")

            return vulnerabilities

        # Test with secure dependencies
        secure_deps = {
            "django": "3.2.0",
            "flask": "2.0.0",
            "requests": "2.28.0",
        }

        vulns = check_dependency_vulnerabilities(secure_deps)
        assert len(vulns) == 0

        # Test with vulnerable dependencies
        vulnerable_deps = {
            "django": "2.0.0",  # Vulnerable version
            "flask": "2.0.0",  # Secure version
        }

        vulns = check_dependency_vulnerabilities(vulnerable_deps)
        assert len(vulns) > 0
        assert "django==2.0.0" in vulns

    def test_security_configuration_validation(self):
        """Test validation of security configuration."""

        def validate_security_config(config):
            """Validate security configuration."""
            issues = []

            # Check debug mode
            if config.get("debug", False):
                issues.append("Debug mode should be disabled in production")

            # Check secret key
            secret_key = config.get("secret_key", "")
            if len(secret_key) < 32:
                issues.append("Secret key should be at least 32 characters")
            if secret_key == "default" or "test" in secret_key:
                issues.append("Default or test secret key detected")

            # Check HTTPS enforcement
            if not config.get("force_https", False):
                issues.append("HTTPS should be enforced")

            # Check session security
            session_config = config.get("session", {})
            if not session_config.get("secure", False):
                issues.append("Session cookies should be secure")
            if not session_config.get("httponly", False):
                issues.append("Session cookies should be HttpOnly")

            return issues

        # Test secure configuration
        secure_config = {
            "debug": False,
            "secret_key": "very-long-and-random-secret-key-for-production-use-only",
            "force_https": True,
            "session": {"secure": True, "httponly": True, "samesite": "Strict"},
        }

        issues = validate_security_config(secure_config)
        assert len(issues) == 0

        # Test insecure configuration
        insecure_config = {
            "debug": True,
            "secret_key": "test",
            "force_https": False,
            "session": {"secure": False, "httponly": False},
        }

        issues = validate_security_config(insecure_config)
        assert len(issues) > 0

    @pytest.mark.asyncio
    async def test_end_to_end_security_flow(self):
        """Test complete security flow from input to output."""
        # Simulate a complete request with security checks

        # 1. Input validation
        malicious_input = {
            "title": "<script>alert('xss')</script>Malicious Title",
            "viewport": {"width": 800, "height": 600},
            "elements": [
                {
                    "type": "text",
                    "content": "javascript:alert('xss')",
                    "style": {"background": "url('javascript:alert(1)')"},
                }
            ],
        }

        # 2. Authentication check (mocked)
        def authenticate_request(token):
            if not token or token == "invalid":
                raise ValueError("Invalid authentication token")
            return {"user_id": "test-user", "permissions": ["render"]}

        # 3. Authorization check
        def authorize_request(user_data, required_permission):
            if required_permission not in user_data.get("permissions", []):
                raise ValueError("Insufficient permissions")

        # 4. Input sanitization
        def sanitize_input(data):
            # Remove script tags and dangerous content
            import re
            import html

            def clean_string(s):
                if isinstance(s, str):
                    s = re.sub(r"<script[^>]*>.*?</script>", "", s, flags=re.IGNORECASE | re.DOTALL)
                    s = re.sub(r"javascript:", "", s, flags=re.IGNORECASE)
                    return html.escape(s)
                return s

            def clean_dict(d):
                if isinstance(d, dict):
                    return {k: clean_dict(v) for k, v in d.items()}
                elif isinstance(d, list):
                    return [clean_dict(item) for item in d]
                else:
                    return clean_string(d)

            return clean_dict(data)

        # Test the complete flow
        try:
            # 1. Authenticate
            user_data = authenticate_request("valid-token")

            # 2. Authorize
            authorize_request(user_data, "render")

            # 3. Sanitize input
            clean_input = sanitize_input(malicious_input)

            # 4. Verify sanitization worked
            assert "<script>" not in str(clean_input)
            assert "javascript:" not in str(clean_input)
            assert "&lt;script&gt;" in str(clean_input) or "alert" not in str(clean_input)

            # 5. Process safely (would continue with DSL parsing, etc.)
            assert clean_input["title"] != malicious_input["title"]  # Should be sanitized

        except ValueError as e:
            pytest.fail(f"Security flow failed: {e}")
