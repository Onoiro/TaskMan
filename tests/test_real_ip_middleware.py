"""
Tests for RealIPMiddleware.

These tests verify that the middleware correctly substitutes
the client IP address when requests come from trusted proxies.
"""
from django.test import TestCase, RequestFactory, override_settings
from unittest.mock import Mock
from task_manager.middleware.real_ip_middleware import RealIPMiddleware


class RealIPMiddlewareTestCase(TestCase):
    """Test cases for RealIPMiddleware."""

    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=Mock(status_code=200))
        self.middleware = RealIPMiddleware(get_response=self.get_response)

    def _create_request(self, remote_addr='127.0.0.1',
                        x_real_ip=None, x_forwarded_for=None):
        """Create a request with given IP settings."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = remote_addr
        if x_real_ip:
            request.META['HTTP_X_REAL_IP'] = x_real_ip
        if x_forwarded_for:
            request.META['HTTP_X_FORWARDED_FOR'] = x_forwarded_for
        return request

    def test_no_trusted_proxies(self):
        """Test that IP is not changed when TRUSTED_PROXIES is not set."""
        request = self._create_request(
            remote_addr='192.168.1.100',
            x_real_ip='203.0.113.50'
        )

        self.middleware(request)

        # IP should remain unchanged
        self.assertEqual(request.META['REMOTE_ADDR'], '192.168.1.100')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1'})
    def test_remote_addr_not_trusted(self):
        """Test that IP is not changed when remote_addr is not trusted."""
        request = self._create_request(
            remote_addr='192.168.1.100',
            x_real_ip='203.0.113.50'
        )

        self.middleware(request)

        # IP should remain unchanged because 192.168.1.100 is not trusted
        self.assertEqual(request.META['REMOTE_ADDR'], '192.168.1.100')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1'})
    def test_real_ip_from_x_real_ip(self):
        """Test that X-Real-IP header is used when present."""
        request = self._create_request(
            remote_addr='10.0.0.1',
            x_real_ip='203.0.113.50'
        )

        self.middleware(request)

        # IP should be replaced with X-Real-IP value
        self.assertEqual(request.META['REMOTE_ADDR'], '203.0.113.50')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1'})
    def test_real_ip_from_x_forwarded_for(self):
        """Test fallback to X-Forwarded-For when X-Real-IP is empty."""
        request = self._create_request(
            remote_addr='10.0.0.1',
            x_forwarded_for='203.0.113.50, 10.0.0.2'
        )

        self.middleware(request)

        # First IP from X-Forwarded-For should be used
        self.assertEqual(request.META['REMOTE_ADDR'], '203.0.113.50')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1'})
    def test_empty_real_ip_unchanged(self):
        """Test that IP is not changed when real_ip headers are empty."""
        request = self._create_request(
            remote_addr='10.0.0.1',
            x_real_ip='',
            x_forwarded_for=''
        )

        self.middleware(request)

        # IP should remain unchanged
        self.assertEqual(request.META['REMOTE_ADDR'], '10.0.0.1')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1'})
    def test_multiple_proxies_forwarded_for(self):
        """Test handling of multiple proxies in X-Forwarded-For."""
        request = self._create_request(
            remote_addr='10.0.0.1',
            x_real_ip='',
            x_forwarded_for='203.0.113.50, 198.51.100.1, 10.0.0.2'
        )

        self.middleware(request)

        # Only the first (client) IP should be used
        self.assertEqual(request.META['REMOTE_ADDR'], '203.0.113.50')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1'})
    def test_x_real_ip_priority_over_forwarded_for(self):
        """Test that X-Real-IP takes priority over X-Forwarded-For."""
        request = self._create_request(
            remote_addr='10.0.0.1',
            x_real_ip='203.0.113.50',
            x_forwarded_for='198.51.100.1'
        )

        self.middleware(request)

        # X-Real-IP should be used, not X-Forwarded-For
        self.assertEqual(request.META['REMOTE_ADDR'], '203.0.113.50')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1'})
    def test_real_ip_with_whitespace(self):
        """Test that whitespace is stripped from IP addresses."""
        request = self._create_request(
            remote_addr='10.0.0.1',
            x_real_ip='  203.0.113.50  '
        )

        self.middleware(request)

        # Whitespace should be stripped
        self.assertEqual(request.META['REMOTE_ADDR'], '203.0.113.50')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1'})
    def test_no_real_ip_headers(self):
        """Test behavior when no real IP headers are present."""
        request = self._create_request(remote_addr='10.0.0.1')

        self.middleware(request)

        # IP should remain unchanged
        self.assertEqual(request.META['REMOTE_ADDR'], '10.0.0.1')

    @override_settings(TRUSTED_PROXIES={'10.0.0.1', '172.16.0.1'})
    def test_multiple_trusted_proxies(self):
        """Test that multiple trusted proxies are all recognized."""
        # Test first proxy
        request1 = self._create_request(
            remote_addr='10.0.0.1',
            x_real_ip='203.0.113.50'
        )
        self.middleware(request1)
        self.assertEqual(request1.META['REMOTE_ADDR'], '203.0.113.50')

        # Test second proxy
        request2 = self._create_request(
            remote_addr='172.16.0.1',
            x_real_ip='198.51.100.10'
        )
        self.middleware(request2)
        self.assertEqual(request2.META['REMOTE_ADDR'], '198.51.100.10')
