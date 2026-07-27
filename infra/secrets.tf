# One Secrets Manager secret holding a JSON blob of all app credentials. ECS
# injects each key as an env var at container start (see ecs.tf `secrets`), so
# no secret ever appears in the task definition, image, or logs.

resource "aws_secretsmanager_secret" "app" {
  name_prefix             = "${var.project_name}/app-"
  recovery_window_in_days = 0 # allow immediate delete on `terraform destroy` (demo)
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    OPENAI_API_KEY = var.openai_api_key
    NEO4J_URI      = var.neo4j_uri
    NEO4J_USER     = var.neo4j_user
    NEO4J_PASSWORD = var.neo4j_password
    QDRANT_URL     = var.qdrant_url
    QDRANT_API_KEY = var.qdrant_api_key
    API_KEYS       = var.api_keys
  })
}
