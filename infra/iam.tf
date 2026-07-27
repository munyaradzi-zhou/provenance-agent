# Two roles, following the ECS convention:
#  - execution role: used by the ECS agent to pull the image, write logs, and
#    read the secret to inject env vars.
#  - task role: assumed by the running container. Our app calls no AWS APIs, so
#    it's intentionally empty (least privilege).

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name_prefix        = "${var.project_name}-exec-"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

# Managed policy: pull from ECR + write to CloudWatch Logs.
resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Extra: allow reading exactly our one secret (nothing else).
data "aws_iam_policy_document" "secrets_read" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.app.arn]
  }
}

resource "aws_iam_role_policy" "secrets_read" {
  name   = "read-app-secret"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.secrets_read.json
}

resource "aws_iam_role" "task" {
  name_prefix        = "${var.project_name}-task-"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}
