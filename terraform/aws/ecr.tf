# - ECR Repository -

resource "aws_ecr_repository" "portfolio_repo" {
  name                 = "portfolio-repo"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Cleanup lifecycle
resource "aws_ecr_lifecycle_policy" "cleanup" {
  repository = aws_ecr_repository.portfolio_repo.name

  policy = <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire untagged images after 30 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 30
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF
}
