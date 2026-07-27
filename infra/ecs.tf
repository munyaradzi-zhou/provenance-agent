# ECS Fargate: the cluster, the task definition (what to run), and the service
# (keep 1 running, register it with the ALB).

resource "aws_cloudwatch_log_group" "app" {
  name_prefix       = "/ecs/${var.project_name}-"
  retention_in_days = 7 # keep logs cheap
}

resource "aws_ecs_cluster" "app" {
  name = var.project_name
}

locals {
  # These keys are read from the JSON secret and injected as env vars.
  secret_keys = [
    "OPENAI_API_KEY", "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD",
    "QDRANT_URL", "QDRANT_API_KEY", "API_KEYS",
  ]
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.project_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name         = "app"
    image        = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]

    # Non-secret config as plain env vars.
    environment = [
      { name = "LLM_MODEL", value = "gpt-4o-mini" },
      { name = "EMBEDDING_MODEL", value = "text-embedding-3-small" },
      { name = "QDRANT_COLLECTION", value = "provenance" },
      { name = "TOP_K", value = "5" },
      { name = "MAX_RETRIES", value = "1" },
      { name = "RATE_LIMIT", value = "60/minute" },
      { name = "REQUEST_TIMEOUT_S", value = "30" },
      { name = "CORS_ORIGINS", value = "*" },
    ]

    # Secrets injected from Secrets Manager (arn:...:JSON_KEY::).
    secrets = [for k in local.secret_keys : {
      name      = k
      valueFrom = "${aws_secretsmanager_secret.app.arn}:${k}::"
    }]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "app"
      }
    }
  }])
}

resource "aws_ecs_service" "app" {
  name            = var.project_name
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE" # on-demand for demo stability; FARGATE_SPOT to cut cost

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true # public subnet + no NAT -> task needs a public IP for egress
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8000
  }

  health_check_grace_period_seconds = 60 # give the app time to boot before health checks
  depends_on                        = [aws_lb_listener.http]
}
