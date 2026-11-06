data "archive_file" "health" {
  type        = "zip"
  source_file = "${path.module}/../../config/monitoring/health_check.py"
  output_path = "${path.root}/.terraform/health-check.zip"
}

resource "aws_cloudwatch_log_group" "health" {
  provider          = aws.us_east_1
  name              = "/aws/lambda/${local.name}-health"
  retention_in_days = 14
}

resource "aws_lambda_function" "health" {
  provider         = aws.us_east_1
  function_name    = "${local.name}-health"
  description      = "Check the public API and website every five minutes."
  role             = aws_iam_role.health.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "health_check.handler"
  filename         = data.archive_file.health.output_path
  source_code_hash = data.archive_file.health.output_base64sha256
  timeout          = 20
  memory_size      = 128
  environment {
    variables = {
      ENVIRONMENT = var.environment
      TARGETS     = jsonencode(local.health_targets)
    }
  }

  depends_on = [aws_iam_role_policy.health, aws_cloudwatch_log_group.health]
}

# A failed invocation must not multiply endpoint requests.
resource "aws_lambda_function_event_invoke_config" "health" {
  provider                     = aws.us_east_1
  function_name                = aws_lambda_function.health.function_name
  maximum_retry_attempts       = 0
  maximum_event_age_in_seconds = 60
}

resource "aws_scheduler_schedule" "health" {
  provider            = aws.us_east_1
  name                = "${local.name}-health"
  description         = "Probe each public endpoint once every five minutes."
  schedule_expression = "rate(5 minutes)"
  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.health.arn
    role_arn = aws_iam_role.health_scheduler.arn
    input    = "{}"
    retry_policy {
      maximum_retry_attempts       = 0
      maximum_event_age_in_seconds = 60
    }
  }

  depends_on = [aws_iam_role_policy.health_scheduler]
}
