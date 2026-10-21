"""Identify noisy unmatched paths for HTTP telemetry filtering."""

SCANNER_PATH_PATTERNS: tuple[str, ...] = (
	r'^/$',
	r'(^|/)\.env(?:[./_-]|$)',
	r'(^|/)[^/]+\.env(?:[./_-]|$)',
	r'^/\.(?:git|svn|hg)(?:/|$)',
	r'^/(?:wp-admin|wp-includes|vendor/phpunit|cgi-bin)(?:/|$)',
	r'^/(?:wp-login|xmlrpc)\.php$',
	r'^/(?:config\.(?:json|js)|api/config|js/env\.js)$',
	r'^/(?:readme|agents|claude)\.md$',
	r'^/\.github/copilot-instructions\.md$',
	r'^/instance/config\.py$',
)
