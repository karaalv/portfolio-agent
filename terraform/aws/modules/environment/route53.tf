resource "aws_route53_record" "api_ipv4" {
  zone_id = data.aws_route53_zone.portfolio.zone_id
  name    = local.api_domain
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.api.domain_name
    zone_id                = aws_cloudfront_distribution.api.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "api_ipv6" {
  zone_id = data.aws_route53_zone.portfolio.zone_id
  name    = local.api_domain
  type    = "AAAA"
  alias {
    name                   = aws_cloudfront_distribution.api.domain_name
    zone_id                = aws_cloudfront_distribution.api.hosted_zone_id
    evaluate_target_health = false
  }
}
