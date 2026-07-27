# Cost tripwire: email alert when this month's spend crosses 80% of $20.
# A safety net so a forgotten ALB/Fargate task can't quietly rack up charges.

variable "alert_email" {
  description = "Email for the budget alert."
  type        = string
  default     = "munyaradzizhou11@gmail.com"
}

resource "aws_budgets_budget" "monthly" {
  name         = "${var.project_name}-monthly"
  budget_type  = "COST"
  limit_amount = "20"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
