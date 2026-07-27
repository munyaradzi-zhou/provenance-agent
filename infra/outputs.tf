output "ecr_repository_url" {
  description = "Push the image here (docker push <this>:<tag>)."
  value       = aws_ecr_repository.app.repository_url
}
