"""Check public endpoints and publish their availability."""

import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def check_endpoint(url: str) -> bool:
	"""Accept a successful HTTPS response within five seconds."""
	request = Request(
		url,
		headers={'User-Agent': 'PortfolioAgent-HealthCheck/1.0'},
	)
	try:
		with urlopen(request, timeout=5) as response:
			return 200 <= response.status < 400
	except (HTTPError, URLError, TimeoutError, OSError):
		return False


def handler(event, context):
	"""Publish one result per target, including failed checks."""
	import boto3

	environment = os.environ['ENVIRONMENT']
	targets = json.loads(os.environ['TARGETS'])
	metrics = []
	results = {}
	for name, target in targets.items():
		healthy = check_endpoint(
			f'https://{target["host"]}{target["path"]}'
		)
		results[name] = healthy
		metrics.append(
			{
				'MetricName': 'Healthy',
				'Dimensions': [
					{'Name': 'Environment', 'Value': environment},
					{'Name': 'Target', 'Value': name},
				],
				'Timestamp': datetime.now(timezone.utc),
				'Value': int(healthy),
				'Unit': 'Count',
			}
		)
	boto3.client('cloudwatch').put_metric_data(
		Namespace='PortfolioAgent/Health', MetricData=metrics
	)
	print(
		json.dumps({'environment': environment, 'results': results})
	)
	return results
