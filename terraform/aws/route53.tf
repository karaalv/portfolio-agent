# - Route 53 Hosted Zone -

resource "aws_route53_zone" "alvinkaranja_dev" {
  comment = "Hosted zone for portfolio."
  name    = "alvinkaranja.dev"
}

# Cloudfront Record
resource "aws_route53_record" "api_domain" {
  zone_id = aws_route53_zone.alvinkaranja_dev.zone_id
  name    = "api.alvinkaranja.dev"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.cloudfront_main.domain_name
    zone_id                = aws_cloudfront_distribution.cloudfront_main.hosted_zone_id
    evaluate_target_health = false
  }
}
