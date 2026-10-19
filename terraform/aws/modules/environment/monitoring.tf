# Route 53 publishes health-check metrics in us-east-1.
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

resource "aws_route53_health_check" "service" {
  for_each          = local.health_targets
  fqdn              = each.value.host
  resource_path     = each.value.path
  type              = "HTTPS"
  port              = 443
  request_interval  = 30
  failure_threshold = 3
  enable_sni        = true
}

resource "aws_cloudwatch_metric_alarm" "health" {
  provider            = aws.us_east_1
  for_each            = local.health_targets
  alarm_name          = "${local.name}-${each.key}-health"
  alarm_description   = "HTTPS health failure for ${each.value.host}${each.value.path}."
  namespace           = "AWS/Route53"
  metric_name         = "HealthCheckStatus"
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  dimensions = {
    HealthCheckId = aws_route53_health_check.service[each.key].id
  }

  alarm_actions = [aws_sns_topic.health.arn]
  ok_actions    = [aws_sns_topic.health.arn]
}
