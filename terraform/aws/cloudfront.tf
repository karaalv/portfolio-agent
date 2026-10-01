# - CloudFront -

# Cache policy
resource "aws_cloudfront_cache_policy" "cache_policy" {
  name        = "cache-policy"
  default_ttl = 0
  min_ttl     = 0
  max_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

# Origin request policy
resource "aws_cloudfront_origin_request_policy" "origin_request_policy" {
  name    = "origin-request-policy"
  comment = "Forward all cookies to origin"

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "allViewer"
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

# Response headers policy
resource "aws_cloudfront_response_headers_policy" "cors_policy" {
  name    = "cors-policy"
  comment = "CORS policy for CloudFront distributions"

  cors_config {
    access_control_allow_credentials = true
    access_control_allow_headers {
      items = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "frontend-token",
        "Connection",
        "Upgrade",
        "Sec-WebSocket-Key",
        "Sec-WebSocket-Version",
        "Sec-WebSocket-Accept",
        "Sec-WebSocket-Protocol"
      ]
    }
    access_control_allow_methods {
      items = ["ALL"]
    }
    access_control_allow_origins {
      items = [
        "https://alvinkaranja.dev",
        "https://api.alvinkaranja.dev",
        "https://staging.alvinkaranja.dev"
      ]
    }
    origin_override            = false
    access_control_max_age_sec = 86400
  }
}

# Main distribution
resource "aws_cloudfront_distribution" "cloudfront_main" {
  enabled = true
  comment = "CloudFront for api.alvinkaranja.dev"

  aliases = ["api.alvinkaranja.dev"]

  origin {
    domain_name = aws_instance.ec2_instance.public_dns
    origin_id   = "api-origin"

    custom_origin_config {
      http_port              = 30001
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "api-origin"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods  = ["GET", "HEAD"]

    cache_policy_id            = aws_cloudfront_cache_policy.cache_policy.id
    origin_request_policy_id   = aws_cloudfront_origin_request_policy.origin_request_policy.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.cors_policy.id
  }

  viewer_certificate {
    acm_certificate_arn = var.acm_arn
    ssl_support_method  = "sni-only"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}
