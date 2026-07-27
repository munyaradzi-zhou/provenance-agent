# CloudWatch dashboard + alarms over the EMF metrics the app emits
# (namespace ProvenanceAgent, dimension service=api).

locals {
  ns  = "ProvenanceAgent"
  dim = { service = "api" }
}

resource "aws_cloudwatch_dashboard" "app" {
  dashboard_name = var.project_name
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "Request latency (ms)"
          region = var.region
          view   = "timeSeries"
          metrics = [
            [local.ns, "Latency", "service", "api", { stat = "p50", label = "p50" }],
            ["...", { stat = "p95", label = "p95" }],
            ["...", { stat = "p99", label = "p99" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6
        properties = {
          title   = "Requests & errors"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            [local.ns, "Requests", "service", "api", { stat = "Sum", label = "requests" }],
            [local.ns, "Errors", "service", "api", { stat = "Sum", label = "5xx errors" }],
          ]
        }
      },
    ]
  })
}

# Alarm: p95 latency too high (agentic path can be slow, but > ~25s is bad).
resource "aws_cloudwatch_metric_alarm" "latency_p95" {
  alarm_name          = "${var.project_name}-p95-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 25000 # ms
  namespace           = local.ns
  metric_name         = "Latency"
  extended_statistic  = "p95"
  period              = 300
  dimensions          = local.dim
  treat_missing_data  = "notBreaching"
}

# Alarm: any 5xx errors in a 5-minute window.
resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.project_name}-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0
  namespace           = local.ns
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  dimensions          = local.dim
  treat_missing_data  = "notBreaching"
}
