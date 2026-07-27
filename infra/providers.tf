provider "aws" {
  region = var.region

  # Tag every resource so it's easy to find (and delete) everything for this project.
  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
    }
  }
}
