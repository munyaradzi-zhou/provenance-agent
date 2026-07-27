# Elastic Container Registry: where the app image lives before ECS pulls it.

resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true # let `terraform destroy` remove images too (demo convenience)

  image_scanning_configuration {
    scan_on_push = true # free vulnerability scan on each push
  }
}

# Keep only the last 5 images so old builds don't accrue storage cost.
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "expire all but the 5 most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}
