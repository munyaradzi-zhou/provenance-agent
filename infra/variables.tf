variable "region" {
  description = "AWS region (must match your `aws configure` region)."
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Name prefix for all resources."
  type        = string
  default     = "provenance-agent"
}

variable "image_tag" {
  description = "ECR image tag to deploy (set by CI to the git SHA)."
  type        = string
  default     = "latest"
}

# --- container sizing (Fargate) ---
variable "task_cpu" {
  description = "Fargate task vCPU units (256 = 0.25 vCPU)."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 1024
}

# --- application secrets (go into Secrets Manager; provided via gitignored tfvars) ---
variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "neo4j_uri" {
  type = string
}

variable "neo4j_user" {
  type    = string
  default = "neo4j"
}

variable "neo4j_password" {
  type      = string
  sensitive = true
}

variable "qdrant_url" {
  type = string
}

variable "qdrant_api_key" {
  type      = string
  sensitive = true
}

variable "api_keys" {
  description = "Comma-separated API keys clients must present."
  type        = string
  sensitive   = true
}

variable "langfuse_public_key" {
  type    = string
  default = ""
}

variable "langfuse_secret_key" {
  type      = string
  sensitive = true
  default   = ""
}
