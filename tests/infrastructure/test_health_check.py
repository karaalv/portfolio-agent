"""Verify scheduled checks report endpoint failures correctly."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

SOURCE = (
	Path(__file__).resolve().parents[2]
	/ 'terraform/aws/config/monitoring/health_check.py'
)
SPEC = importlib.util.spec_from_file_location('health_check', SOURCE)
assert SPEC is not None and SPEC.loader is not None
health_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(health_check)


def test_successful_response_is_healthy():
	"""An HTTPS success counts as a healthy target."""
	with patch.object(health_check, 'urlopen') as open_url:
		open_url.return_value.__enter__.return_value.status = 200
		assert health_check.check_endpoint('https://example.com/')
		assert open_url.call_args.kwargs['timeout'] == 5


@pytest.mark.parametrize(
	'error',
	[
		HTTPError(
			'https://example.com/', 503, 'Unavailable', {}, None
		),
		URLError('connection failed'),
		TimeoutError('timed out'),
	],
)
def test_failed_request_is_unhealthy(error):
	"""HTTP, connection and timeout errors publish failure."""
	with patch.object(health_check, 'urlopen', side_effect=error):
		assert not health_check.check_endpoint('https://example.com/')


def test_failed_target_does_not_skip_other_target(monkeypatch):
	"""Both targets emit metrics even when the API is down."""
	monkeypatch.setenv('ENVIRONMENT', 'production')
	monkeypatch.setenv(
		'TARGETS',
		json.dumps(
			{
				'api': {'host': 'api.example.com', 'path': '/health'},
				'website': {'host': 'example.com', 'path': '/'},
			}
		),
	)
	client = MagicMock()
	sdk = SimpleNamespace(client=MagicMock(return_value=client))
	with (
		patch.dict(sys.modules, {'boto3': sdk}),
		patch.object(
			health_check, 'check_endpoint', side_effect=[False, True]
		) as check,
	):
		assert health_check.handler({}, None) == {
			'api': False,
			'website': True,
		}
	assert check.call_count == 2
	metrics = client.put_metric_data.call_args.kwargs['MetricData']
	assert [metric['Value'] for metric in metrics] == [0, 1]
	assert [metric['Dimensions'] for metric in metrics] == [
		[
			{'Name': 'Environment', 'Value': 'production'},
			{'Name': 'Target', 'Value': name},
		]
		for name in ('api', 'website')
	]
