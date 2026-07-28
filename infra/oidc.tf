# GitHub Actions -> AWS via OIDC (no long-lived access keys).
#
# 1. Register GitHub's OIDC token issuer as a trusted identity provider.
# 2. Create a deploy role that ONLY a workflow from this repo's `main` branch may
#    assume, and that can ONLY push to our ECR repo + roll the ECS service.
#
# The workflow (.github/workflows/deploy.yml) requests a short-lived token from
# GitHub, AWS STS verifies it against this provider + trust policy, and hands
# back ~1h credentials. Nothing is stored in GitHub secrets.

# --- the trusted identity provider ------------------------------------------
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"] # the audience GitHub's token must carry
  # Thumbprints of GitHub's OIDC TLS cert chain. AWS no longer validates these
  # for the GitHub provider (it uses its own trust store), but the field is still
  # required. Both current values are listed for resilience.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fce",
  ]
}

# --- who may assume the deploy role -----------------------------------------
# Federated principal = the provider above. Two conditions:
#  - aud must be exactly sts.amazonaws.com (blocks tokens minted for other audiences)
#  - sub must match THIS repo on the main branch (blocks every other repo/branch/PR)
data "aws_iam_policy_document" "github_deploy_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name_prefix        = "${var.project_name}-deploy-"
  assume_role_policy = data.aws_iam_policy_document.github_deploy_assume.json
}

# --- what the deploy role may do (least privilege) --------------------------
data "aws_iam_policy_document" "github_deploy" {
  # ECR auth token is an account-level action (no resource scoping possible).
  statement {
    sid       = "EcrAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # Push/pull layers + images, but only to OUR repository.
  statement {
    sid = "EcrPushPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = [aws_ecr_repository.app.arn]
  }

  # Roll the service onto the freshly-pushed image and let CI wait for stable.
  # `update-service --force-new-deployment` reuses the existing task definition,
  # so we need neither RegisterTaskDefinition nor iam:PassRole here.
  statement {
    sid       = "EcsDeploy"
    actions   = ["ecs:UpdateService", "ecs:DescribeServices"]
    resources = [aws_ecs_service.app.id]
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "deploy-ecr-ecs"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}
