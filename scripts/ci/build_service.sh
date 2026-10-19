#!/usr/bin/env bash
# Prepare the tested revision and delegate operations to Make.
set -euo pipefail
umask 077

: "${BUCKET_NAME:?Supply the CI scripts bucket}"
: "${SOURCE_LOCATION:?Supply the source bundle S3 key}"
: "${COMMIT_SHA:?Supply the tested Git commit SHA}"
: "${PORTFOLIO_AGENT_ENV:?Select staging or production}"

case "$PORTFOLIO_AGENT_ENV" in
  staging|production) ;;
  *)
    echo "[ci] Invalid deployment environment: $PORTFOLIO_AGENT_ENV" >&2
    exit 1
    ;;
esac

if [[ ! "$COMMIT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "[ci] COMMIT_SHA must be a complete Git commit SHA." >&2
  exit 1
fi

work_dir="$(mktemp -d -t portfolio-agent-build.XXXXXX)"
trap 'result=$?; rm -rf -- "$work_dir" || true; exit "$result"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "[ci] Downloading source for $COMMIT_SHA from the CI bucket."
aws s3 cp "s3://$BUCKET_NAME/$SOURCE_LOCATION" \
  "$work_dir/source.bundle" --region eu-west-2

echo "[ci] Checking out the revision that passed tests."
git clone --quiet --no-checkout "$work_dir/source.bundle" \
  "$work_dir/portfolio-agent"
cd "$work_dir/portfolio-agent"
git checkout --quiet --detach "$COMMIT_SHA"
if [[ "$(git rev-parse HEAD)" != "$COMMIT_SHA" ]]; then
  echo "[ci] Source revision does not match the tested commit." >&2
  exit 1
fi


echo "[ci] Running make build-push for $PORTFOLIO_AGENT_ENV at $COMMIT_SHA."
make build-push

echo "[ci] build completed successfully for $PORTFOLIO_AGENT_ENV."
