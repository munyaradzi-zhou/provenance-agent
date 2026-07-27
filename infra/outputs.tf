output "ecr_repository_url" {
  description = "Push the image here (docker push <this>:<tag>)."
  value       = aws_ecr_repository.app.repository_url
}

output "api_url" {
  description = "Public HTTPS endpoint (API Gateway)."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "alb_url" {
  description = "ALB URL (HTTP; behind API Gateway)."
  value       = "http://${aws_lb.app.dns_name}"
}

output "ecs_cluster" {
  value = aws_ecs_cluster.app.name
}

output "ecs_service" {
  value = aws_ecs_service.app.name
}
