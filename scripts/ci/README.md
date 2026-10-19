# Service CI/CD scripts

This folder contains scripts used to build, publish and deploy
Portfolio Agent. GitHub Actions uploads them to S3 for execution
by CodeBuild and the EC2 SSM action.

Workflows live in `.github/workflows/`:

- `push_to_main.yaml`: testing on `main`.
- `push_to_staging.yaml`: testing, build and staging deployment.
- `push_to_prod.yaml`: testing, build and production deployment.

## Branch behaviour

| Push branch | Operations |
| --- | --- |
| `main` | Run the complete pytest suite. |
| `staging` | Tests, native ARM build/push, deploy to staging EC2. |
| `production` | Tests, native ARM build/push, deploy to production EC2. |

Deployment jobs run only after tests and the build succeed.
Runs are serialised per branch without cancelling an active
remote deployment. The workflow does not provision or start EC2.

## Manual runs

All three workflows also declare `workflow_dispatch`.
After the files exist on the repository's default branch:

1. Open the repository's **Actions** tab.
2. Select **Testing on main**, **Deploy to Staging** or
   **Deploy to Production**.
3. Click **Run workflow** and select the matching branch.
4. Click **Run workflow** to confirm.

Select `main`, `staging` or `production` respectively. Each
workflow is guarded against running on another branch. Manual
deployments run tests and rebuild before deploying; they do not
skip straight to deployment or start a stopped EC2 instance.
The workflow file must also exist on the selected branch.

From the repository root, the equivalent CLI commands are:

```sh
gh workflow run push_to_main.yaml --ref main
gh workflow run push_to_staging.yaml --ref staging
gh workflow run push_to_prod.yaml --ref production
```

No new commit is needed. GitHub environment approval rules still
apply to manually triggered deployments.

## Scripts

### `build_service.sh`

Runs in `portfolio-agent-arm-codebuild`. Downloads the tested
source bundle, checks out the exact commit and runs
`make build-push`. The Makefile owns registry authentication,
repository naming, image tags and Docker build settings.

### `deploy_service.sh`

Runs through SSM as root on the selected EC2 node. Downloads the
same source bundle, checks out the same commit, selects the
existing private k3s kubeconfig and runs `make deploy`.

The Makefile owns secret selection and refresh, image lookup,
manifest rendering and rollout readiness. The script does not
override the secret ID, image tag, region or NodePort.

Both scripts validate their inputs and clean private temporary
workspaces on success, failure or handled interruption. They do
not modify kubeconfig permissions or prune Docker images.

## Inputs

| Variable | Purpose |
| --- | --- |
| `PORTFOLIO_AGENT_ENV` | `staging` or `production`; the only service deployment setting passed to Make. |
| `BUCKET_NAME` | Shared CI scripts/source bucket. |
| `SOURCE_LOCATION` | S3 key of the tested Git source bundle. |
| `COMMIT_SHA` | Full Git SHA that must be checked out. |

CodeBuild additionally receives `SCRIPT_LOCATION` for its
bootstrap buildspec to download `build_service.sh`.

## Source and script hand-off

After tests pass, GitHub checks out the triggering commit with
full history and creates a self-contained Git bundle. The
bundle contains committed source and its Git history, allowing
the Makefile to derive the same commit tag during build and
deployment. Untracked `.env` files and checkout credentials
are not included. No repository deploy key is needed for these
CI scripts.

The workflow uploads the bundle and both scripts to:

```text
s3://533267122031-portfolio-agent-ci-cd-scripts/
  ci/<commit-sha>/<run-id>-<attempt>/
    source.bundle
    build_service.sh
    deploy_service.sh
```

Each run uses its own prefix. A branch moving while a build is
running cannot change the source selected for that deployment.
The workflow uploads scripts automatically; no manual upload is
required after editing them. Source bundles retain history, so
full history is fetched before creating them.

## GitHub configuration

Create these repository Actions secrets:

| Secret | Value |
| --- | --- |
| `ENV_TEST_FILE` | Complete `.env.testing` contents with testing-only credentials and `PORTFOLIO_AGENT_ENV=testing`. |
| `AWS_OIDC_ROLE` | ARN output by the shared Terraform root as `github_actions_role_arn`. |

Deployment jobs reference GitHub environments named `staging`
and `production`. Configure any desired environment protection
rules there. Keep the OIDC role secret repository-scoped so the
build job can use it before the deployment environment gate.

Tests use uv, Python 3.14 and `requirements.txt`, then run
`.venv/bin/python -m pytest`. They include live MongoDB/OpenAI
integration tests. The testing corpus/index must already be
bootstrapped, the runner must be permitted by Atlas network
access, and testing credentials must be valid. The workflow
does not broaden Atlas access or bootstrap data automatically.
It writes `.env.testing` privately and removes it afterwards.
No production settings are used by the test job.

Before deployment, apply the shared and environment Terraform
roots. EC2 must be running, registered with SSM and have a ready
k3s node. Runtime Secrets Manager entries must match the
Makefile's environment-specific IDs and contain the correct
application configuration. The instance needs Atlas access.

The Terraform IAM policies already cover source/script reads,
image publication/pulls, SSM execution and logging. These CI
scripts do not require `build_secret_arns` to include a Git key.

## Logs and failure handling

CodeBuild logs are streamed by
`aws-actions/aws-codebuild-run-build@v1` from:

```text
/aws/codebuild/portfolio-agent-arm-codebuild
```

Deployments use `karaalv/aws-ec2-ssm-script-runner@v0`.
CloudWatch logging is enabled and sent to:

```text
/aws/ssm/portfolio-agent/deployments
```

The action relays CloudWatch output into the workflow log,
retaining direct SSM output as a fallback. Command IDs identify
stdout/stderr streams. Both groups retain logs for 30 days.

Build or deployment errors fail the workflow. The deployment
script waits for the Makefile's Kubernetes rollout check.
Remote cancellation is best effort; workflow concurrency avoids
automatically cancelling an active deployment. No automatic
rollback or public HTTP/WebSocket smoke test is added here.

The workflows were merged into `main` through PR #9 on
19 October 2026. [Testing on main](https://github.com/karaalv/portfolio-agent/actions/runs/39221870992)
passed at merge commit `d58b2ba`. CodeBuild and SSM deployment
have not yet been verified against AWS. The custom action
remains a prerelease pending live validation.
