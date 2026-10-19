# Portfolio Agent infrastructure

Infrastructure uses separate Terraform roots for shared AWS
resources, staging, production and MongoDB Atlas. The existing
S3 state bucket is managed by the local bootstrap root.

See the [Terraform guide](../../terraform/README.md) and
[AWS configuration](../../terraform/aws/README.md).
These documents describe source configuration, not a verified
live deployment.

## Ownership and isolation

Shared state owns the CI scripts bucket, the `portfolio-agent`
ECR repository, GitHub OIDC role, native ARM CodeBuild project
and deployment log groups. It survives staging teardown.

Staging and production reuse one environment module but have
independent state, EC2 nodes, IAM profiles, CloudFront API
policies/distributions, API aliases and health monitoring.
The `alvinkaranja.dev` hosted zone is read as data. Vercel website
hosting and frontend DNS remain separately managed. No WAF is
configured.

Each environment uses one `t4g.small` node with a 40 GB encrypted
gp3 root volume, IMDSv2, Docker and k3s. Both expose NodePort
`30001` on different machines. API ingress is limited to
CloudFront's origin-facing prefix list. Administration uses SSM.
The bootstrap template installs the host software and attempts
to deploy an existing image from the selected Git revision.

## Public endpoints

| Environment | API | Website health check |
| --- | --- | --- |
| Staging | `api.staging.alvinkaranja.dev` | `staging.alvinkaranja.dev` |
| Production | `api.alvinkaranja.dev` | `alvinkaranja.dev` |

CloudFront terminates TLS and forwards uncached HTTP/WebSocket
traffic to the node on HTTP port `30001`. Viewer headers,
cookies and query parameters are forwarded, including PostHog
session and distinct ID headers. Credentialled CORS uses the
corresponding frontend/API origins. Certificates are supplied
per environment and must be issued in `us-east-1`.

Route 53 checks the API at `/api/system/health` and the website
at `/`. CloudWatch alarms and SNS notifications are hosted in
`us-east-1`, where Route 53 health metrics are published.
Recipients must confirm their SNS email subscriptions.

## Persistent data

Atlas retains development, test and production projects in its
own state. The M0 clusters use AWS Ireland (`EU_WEST_1`).
Development and test access is restricted to the configured
trusted client `/32`. Production reads the node IP from
`aws/production/terraform.tfstate` when remote lookup is enabled.
This lookup does not change MongoDB's own state location.
Staging's selected database project also needs its node allowlist
configured before the app can connect. No extra Atlas project
is introduced by this AWS restructuring.

EC2 public addresses can change on replacement or stop/start.
Review the CloudFront origin and update Atlas access afterwards.
Destroying staging AWS resources does not delete Atlas data,
shared registry images, shared scripts or deployment logs.

## Deployment configuration

Only `PORTFOLIO_AGENT_ENV=production` selects production in the
Makefile; other values select staging. Both use port `30001`,
separate Deployment/Service names and environment secrets.
Secrets Manager paths default to `portfolio-agent/env/staging`
and `portfolio-agent/env/production`. Bootstrap leaves secret selection
to the Makefile. Deployment and rollout refresh
registry and environment secrets before changing pods.

The default AMI is pinned to Ubuntu 26.04 LTS ARM64 image serial
`20261003` in London. Changing user data does not automatically
replace or reprovision an existing node. Terraform completion
also does not verify cloud-init or application startup.

SSM deployment output uses the shared CloudWatch log group
`/aws/ssm/portfolio-agent/deployments`, retained for 30 days.
The caller must enable CloudWatch output on each Run Command.
See the AWS guide for action integration and log correlation.
