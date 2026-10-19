resource "aws_cloudfront_cache_policy" "api" {
  name        = "${local.name}-no-cache"
  comment     = "Disable caching for authenticated HTTP and WebSocket traffic."
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

resource "aws_cloudfront_origin_request_policy" "api" {
  name    = "${local.name}-origin"
  comment = "Forward cookies, queries, WebSocket and PostHog tracing headers."
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

resource "aws_cloudfront_response_headers_policy" "api" {
  name    = "${local.name}-cors"
  comment = "Credentialled CORS for the ${var.environment} portfolio frontend."
  cors_config {
    access_control_allow_credentials = true
    access_control_allow_headers {
      items = [
        "Content-Type", "Authorization", "X-Requested-With", "X-Request-ID",
        "X-POSTHOG-SESSION-ID", "X-POSTHOG-DISTINCT-ID",
        "Connection", "Upgrade", "Sec-WebSocket-Key", "Sec-WebSocket-Version",
        "Sec-WebSocket-Accept", "Sec-WebSocket-Protocol", "Sec-WebSocket-Extensions"
      ]
    }

    access_control_allow_methods {
      items = ["ALL"]
    }

    access_control_allow_origins {
      items = ["https://${local.site_domain}", "https://${local.api_domain}"]
    }

    access_control_expose_headers {
      items = ["X-Request-ID"]
    }

    origin_override            = true
    access_control_max_age_sec = 86400
  }
}

resource "aws_cloudfront_distribution" "api" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "Portfolio Agent ${var.environment} HTTP and WebSocket API."
  aliases         = [local.api_domain]
  price_class     = "PriceClass_200"
  origin {
    domain_name = aws_instance.node.public_dns
    origin_id   = local.name
    custom_origin_config {
      http_port              = 30001
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id           = local.name
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = aws_cloudfront_cache_policy.api.id
    origin_request_policy_id   = aws_cloudfront_origin_request_policy.api.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.api.id
  }

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}
