# API Gateway HTTP API = the public HTTPS front door. It gives us a managed TLS
# endpoint (no domain/ACM needed) and edge throttling, proxying to the ALB.

resource "aws_apigatewayv2_api" "http" {
  name          = var.project_name
  protocol_type = "HTTP"
}

# Proxy every path through to the ALB over HTTP.
resource "aws_apigatewayv2_integration" "alb" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "ANY"
  integration_uri        = "http://${aws_lb.app.dns_name}/{proxy}"
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.alb.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  # Edge throttling (belt-and-braces with the app's own slowapi limiter).
  default_route_settings {
    throttling_burst_limit = 20
    throttling_rate_limit  = 50
  }
}
