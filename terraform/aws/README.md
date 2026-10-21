# AWS infrastructure

The AWS configuration has three independent roots. Regional
resources use London (`eu-west-2`), with Route 53 health alarms
and their SNS topics in `us-east-1`.

| Root | Responsibility | S3 state key |
| --- | --- | --- |
| `shared/` | CI scripts, ECR, GitHub OIDC role, CodeBuild and logs | `aws/shared/terraform.tfstate` |
| `staging/` | Staging node, API distribution, records and health monitoring | `aws/staging/terraform.tfstate` |
| `production/` | Production node, API distribution, records and health monitoring | `aws/production/terraform.tfstate` |

All use bucket
`portfolio-agent-tfstate-eu-west-2-533267122031`, native S3
lockfiles and encrypted state. The reusable `modules/environment`
module owns no backend; its resources belong to the calling root.
The old flat `aws/` directory is no longer an executable root.

## Configure and initialise

```sh
export AWS_PROFILE=karaalv-sandbox
export AWS_REGION=eu-west-2
aws sts get-caller-identity

terraform -chdir=terraform/aws/shared init
terraform -chdir=terraform/aws/staging init
terraform -chdir=terraform/aws/production init
```

Create ignored `terraform.tfvars` files where inputs are needed,
using each root's `variables.tf` as the reference. Example files
are not shipped. Fill in each environment's certificate and
secret ARNs. The module discovers London's default VPC and
selects the first
default subnet by sorted subnet ID. The default network must
retain its public routing and DNS configuration. Certificates
must be issued in `us-east-1` and cover the corresponding API
hostname.

An existing account-wide GitHub OIDC provider must be supplied
through `github_oidc_provider_arn`, or imported into shared state.
Do not create a second provider for the same issuer.

Apply shared first, then the desired environment. Environment
roots read shared outputs from S3. Review a saved plan before
applying. The previous AWS infrastructure was fully torn down,
so these roots start fresh without a state migration.

```sh
terraform -chdir=terraform/aws/shared plan -out=shared.tfplan
terraform -chdir=terraform/aws/shared apply shared.tfplan
terraform -chdir=terraform/aws/staging plan -out=staging.tfplan
terraform -chdir=terraform/aws/staging apply staging.tfplan
```

To retire staging, review and apply a destroy plan only from
`terraform/aws/staging`. This also removes its API distribution,
API DNS records, health checks, SNS topic and node disk. Shared
images, scripts and logs, MongoDB, frontend DNS and the hosted
zone remain outside that state.

## Shared resources

- S3: `533267122031-portfolio-agent-ci-cd-scripts`, versioned,
  encrypted, public access blocked and HTTPS required.
- ECR: `portfolio-agent`, shared by both environments. Untagged
  images expire after 30 days. Tags remain mutable because the
  current Makefile also updates `latest`; use commit tags when
  selecting deployments.
- GitHub role: `portfolio-agent-github-actions`, with repository
  access across branches, tags, environments and pull requests.
  The trust policy checks the OIDC audience and repository.
- CodeBuild: `portfolio-agent-arm-codebuild`, native ARM small
  compute, privileged Docker and the maintained Amazon Linux
  ARM image. Its generic buildspec runs an S3 script and cleans
  its temporary directory on success or failure.
- CloudWatch: separate SSM and CodeBuild groups, retained for
  30 days. Staging teardown does not delete these groups.

CodeBuild receives `BUCKET_NAME` by default. Each invocation must
supply `SCRIPT_LOCATION`, ideally a commit-specific object key.
The script is responsible for obtaining source, authenticating
Docker and executing build steps. `NO_SOURCE` does not check out
GitHub automatically. Supply exact source and image revisions
through invocation variables. Grant any required repository-key
secret ARN explicitly through `build_secret_arns`.

## Environment resources

| Setting | Staging | Production |
| --- | --- | --- |
| Instance Name | `portfolio-agent-staging` | `portfolio-agent-production` |
| API hostname | `api.staging.alvinkaranja.dev` | `api.alvinkaranja.dev` |
| Website health target | `staging.alvinkaranja.dev` | `alvinkaranja.dev` |
| Initial Git ref | `staging` | `production` |
| NodePort | `30001` | `30001` |

Each root creates a `t4g.small`, encrypted 40 GB gp3 root disk,
IMDSv2-only metadata, instance IAM profile, CloudFront API
policies/distribution, IPv4/IPv6 API aliases and health monitoring.
The security group accepts application traffic only from the
CloudFront origin-facing prefix list. Administration uses SSM;
no inbound SSH rule or key pair is required.

The existing `alvinkaranja.dev` public hosted zone is a data
source. Website records remain managed with frontend hosting.
No WAF is configured. All taggable resources use
`Project=portfolio-agent` and `ManagedBy=terraform`. Only EC2 adds
`Name`, which the deployment action requires for instance lookup.

CloudFront disables caching, forwards all viewer headers,
cookies and query parameters, and allows credentialled CORS
for the environment's website and API origins. This includes
`X-POSTHOG-SESSION-ID`, `X-POSTHOG-DISTINCT-ID` and WebSocket
headers. Application origin checks must allow the same origins.
The origin remains HTTP on port `30001`, with viewer TLS
terminated by CloudFront.

Health checks use `/api/system/health` for the API and `/` for
the website. Route 53 checks every 30 seconds with a failure
threshold of three. CloudWatch alarms evaluate three one-minute
periods and notify on alarm and recovery. `alarm_emails` defaults
to `alvinnjiiri@gmail.com`. Confirm each SNS email subscription
to receive alerts.
These checks monitor the existing Vercel sites but do not manage
or deploy them.

## Pinned image and bootstrap

The default AMI is `ami-00627c8cb63796b98`: Canonical Ubuntu
26.04 LTS ARM64, London, image serial `20261003`. It was selected
from Canonical's public catalogue on 18 October 2026 as the
latest available London image for the current LTS release.
The AMI ID is fixed, with owner and architecture checks. Upgrades
require an explicit variable/configuration change and plan.

`config/ec2/setup.sh.tftpl` installs the ARM AWS CLI, SSM, Docker
and k3s using the existing Docker runtime model. It retains
private root-only kubeconfig permissions. Cloud-init handles
root-disk expansion. The script obtains the raw repository SSH
key from Secrets Manager, verifies GitHub host keys from its
HTTPS metadata endpoint, checks out `deployment_ref` and runs
`make deploy` with only `PORTFOLIO_AGENT_ENV` set for deployment
selection. The Makefile resolves the secret ID, image tag and
NodePort.
Temporary credentials and source are removed on exit.

The ECR image must already exist under the tag resolved by the
Makefile from the checked-out Git revision. The script does not
build images or override Makefile deployment settings.
Runtime secrets must provide the correct origins, cookie domain
and application environment. No secret values are stored in
user data, only secret ARNs.

The node uses an automatically assigned public IP. After node
replacement or a stop/start, review CloudFront's origin and
reapply MongoDB access configuration with the new IP. Staging
also needs its selected Atlas project's network allowlist
configured. Atlas reads the production node IP from
`aws/production/terraform.tfstate`; this lookup requires that
state to exist and does not change MongoDB's own backend. Terraform apply does not wait for cloud-init
or prove the application deployed successfully. If database
access is configured after node creation, the initial deploy
may fail; redeploy through SSM after Atlas is ready. Inspect
`/var/log/cloud-init-output.log` for bootstrap failures.

Changes to user data do not replace an existing node or rerun
cloud-init. To use a changed bootstrap, deliberately replace the
node after reviewing the plan, or apply the required host change
through SSM. The k3s installer follows its stable channel;
the application environment stays single-node and single-worker.

## SSM invocation logs

The shared log group is
`/aws/ssm/portfolio-agent/deployments`. EC2 instance roles can
create streams and write events there; GitHub can read them.
SSM Agent streams stdout/stderr directly from the node, so no
separate CloudWatch agent is required for command output.

Creating the group does not enable logging on commands. The
EC2 helper action must include this option in `ssm send-command`:

```sh
--cloud-watch-output-config \
  'CloudWatchOutputEnabled=true,CloudWatchLogGroupName=/aws/ssm/portfolio-agent/deployments'
```

The CI/CD workflow enables this option through the personal
`aws-ec2-ssm-script-runner` action and streams CloudWatch output
into GitHub. Terraform supplies the destination and permissions.
See the [CI script guide](../../scripts/ci/README.md).

Streams identify the command, instance and execution plugin,
with separate stdout/stderr streams. Use the returned command
ID to correlate a GitHub run with its logs. AWS uploads output
periodically, so it is not necessarily immediate. Avoid shell
tracing around secret retrieval and export operations. These
are deployment-command logs, not application logs or a CloudTrail
audit of AWS API calls. CodeBuild writes its own build output
automatically to `/aws/codebuild/portfolio-agent-arm-codebuild`.

## Sources

- [Canonical image discovery](https://ubuntu.com/aws/docs/aws-how-to/instances/find-ubuntu-images/)
- [Canonical released AWS image catalogue](https://cloud-images.ubuntu.com/releases/streams/v1/com.ubuntu.cloud:released:aws.json)
- [CodeBuild compute types](https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-compute-types.html)
- [SSM Run Command CloudWatch logging](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-rc-setting-up-cwlogs.html)
