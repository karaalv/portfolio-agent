# Keep monitoring in the same region as the existing SNS topic.
resource "aws_sns_topic" "health" {
  provider = aws.us_east_1
  name     = "${local.name}-health-alerts"
}

resource "aws_sns_topic_subscription" "health" {
  provider  = aws.us_east_1
  for_each  = var.alarm_emails
  topic_arn = aws_sns_topic.health.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_cloudwatch_metric_alarm" "health" {
  provider            = aws.us_east_1
  for_each            = local.health_targets
  alarm_name          = "${local.name}-${each.key}-health"
  alarm_description   = "HTTPS health failure for ${each.value.host}${each.value.path}."
  namespace           = "PortfolioAgent/Health"
  metric_name         = "Healthy"
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  dimensions = {
    Environment = var.environment
    Target      = each.key
  }

  alarm_actions = [aws_sns_topic.health.arn]
  ok_actions    = [aws_sns_topic.health.arn]
}
