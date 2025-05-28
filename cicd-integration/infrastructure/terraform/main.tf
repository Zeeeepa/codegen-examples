# Enterprise CI/CD Infrastructure with Multi-Cloud Support
# This Terraform configuration sets up a comprehensive CI/CD infrastructure
# with monitoring, security, and disaster recovery capabilities

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
    datadog = {
      source  = "DataDog/datadog"
      version = "~> 3.20"
    }
  }
  
  backend "s3" {
    bucket         = "enterprise-terraform-state"
    key            = "cicd-infrastructure/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# ============================================================================
# VARIABLES
# ============================================================================

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  default     = "staging"
}

variable "application_name" {
  description = "Application name"
  type        = string
  default     = "enterprise-app"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

variable "enable_multi_cloud" {
  description = "Enable multi-cloud deployment"
  type        = bool
  default     = false
}

variable "enable_disaster_recovery" {
  description = "Enable disaster recovery setup"
  type        = bool
  default     = true
}

variable "monitoring_retention_days" {
  description = "Monitoring data retention in days"
  type        = number
  default     = 30
}

variable "backup_retention_days" {
  description = "Backup retention in days"
  type        = number
  default     = 90
}

# ============================================================================
# DATA SOURCES
# ============================================================================

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# ============================================================================
# NETWORKING
# ============================================================================

module "vpc" {
  source = "./modules/vpc"
  
  name               = "${var.application_name}-${var.environment}"
  cidr               = "10.0.0.0/16"
  availability_zones = var.availability_zones
  
  enable_nat_gateway   = true
  enable_vpn_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = local.common_tags
}

# ============================================================================
# EKS CLUSTER
# ============================================================================

module "eks" {
  source = "./modules/eks"
  
  cluster_name    = "${var.application_name}-${var.environment}"
  cluster_version = "1.27"
  
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  
  # Node groups configuration
  node_groups = {
    general = {
      desired_capacity = 3
      max_capacity     = 10
      min_capacity     = 1
      
      instance_types = ["t3.medium", "t3.large"]
      capacity_type  = "ON_DEMAND"
      
      k8s_labels = {
        Environment = var.environment
        NodeGroup   = "general"
      }
      
      k8s_taints = []
    }
    
    spot = {
      desired_capacity = 2
      max_capacity     = 20
      min_capacity     = 0
      
      instance_types = ["t3.medium", "t3.large", "t3.xlarge"]
      capacity_type  = "SPOT"
      
      k8s_labels = {
        Environment = var.environment
        NodeGroup   = "spot"
      }
      
      k8s_taints = [
        {
          key    = "spot"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      ]
    }
  }
  
  # OIDC provider for service accounts
  enable_irsa = true
  
  tags = local.common_tags
}

# ============================================================================
# APPLICATION LOAD BALANCER
# ============================================================================

module "alb" {
  source = "./modules/alb"
  
  name               = "${var.application_name}-${var.environment}"
  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.public_subnets
  security_group_ids = [aws_security_group.alb.id]
  
  enable_deletion_protection = var.environment == "production"
  enable_http2              = true
  enable_cross_zone_load_balancing = true
  
  # SSL/TLS configuration
  certificate_arn = aws_acm_certificate.main.arn
  ssl_policy      = "ELBSecurityPolicy-TLS-1-2-2017-01"
  
  tags = local.common_tags
}

# ============================================================================
# SECURITY GROUPS
# ============================================================================

resource "aws_security_group" "alb" {
  name_prefix = "${var.application_name}-${var.environment}-alb"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.application_name}-${var.environment}-alb"
  })
}

# ============================================================================
# SSL CERTIFICATE
# ============================================================================

resource "aws_acm_certificate" "main" {
  domain_name       = var.environment == "production" ? "app.example.com" : "${var.environment}.example.com"
  validation_method = "DNS"
  
  subject_alternative_names = [
    "*.${var.environment == "production" ? "app.example.com" : "${var.environment}.example.com"}"
  ]
  
  lifecycle {
    create_before_destroy = true
  }
  
  tags = local.common_tags
}

# ============================================================================
# RDS DATABASE
# ============================================================================

module "rds" {
  source = "./modules/rds"
  
  identifier = "${var.application_name}-${var.environment}"
  
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = var.environment == "production" ? "db.r6g.large" : "db.t3.micro"
  
  allocated_storage     = var.environment == "production" ? 100 : 20
  max_allocated_storage = var.environment == "production" ? 1000 : 100
  storage_encrypted     = true
  
  db_name  = replace("${var.application_name}_${var.environment}", "-", "_")
  username = "app_user"
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = var.backup_retention_days
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  # Enhanced monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_enhanced_monitoring.arn
  
  # Performance insights
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  
  deletion_protection = var.environment == "production"
  
  tags = local.common_tags
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.application_name}-${var.environment}-rds"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description     = "PostgreSQL"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.application_name}-${var.environment}-rds"
  })
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.application_name}-${var.environment}"
  subnet_ids = module.vpc.private_subnets
  
  tags = local.common_tags
}

# ============================================================================
# REDIS CACHE
# ============================================================================

module "redis" {
  source = "./modules/redis"
  
  cluster_id           = "${var.application_name}-${var.environment}"
  node_type           = var.environment == "production" ? "cache.r6g.large" : "cache.t3.micro"
  num_cache_nodes     = var.environment == "production" ? 3 : 1
  parameter_group_name = "default.redis7"
  port                = 6379
  
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  # Backup configuration
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window         = "03:00-05:00"
  
  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = local.common_tags
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.application_name}-${var.environment}-redis"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description     = "Redis"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.application_name}-${var.environment}-redis"
  })
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.application_name}-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

# ============================================================================
# S3 BUCKETS
# ============================================================================

# Application assets bucket
resource "aws_s3_bucket" "assets" {
  bucket = "${var.application_name}-${var.environment}-assets-${random_id.bucket_suffix.hex}"
  
  tags = local.common_tags
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "assets" {
  bucket = aws_s3_bucket.assets.id
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

# Backup bucket
resource "aws_s3_bucket" "backups" {
  bucket = "${var.application_name}-${var.environment}-backups-${random_id.bucket_suffix.hex}"
  
  tags = local.common_tags
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  
  rule {
    id     = "backup_lifecycle"
    status = "Enabled"
    
    expiration {
      days = var.backup_retention_days
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ============================================================================
# MONITORING AND OBSERVABILITY
# ============================================================================

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/eks/${var.application_name}-${var.environment}/application"
  retention_in_days = var.monitoring_retention_days
  
  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "infrastructure" {
  name              = "/aws/eks/${var.application_name}-${var.environment}/infrastructure"
  retention_in_days = var.monitoring_retention_days
  
  tags = local.common_tags
}

# Prometheus and Grafana via Helm
resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = "monitoring"
  version    = "51.2.0"
  
  create_namespace = true
  
  values = [
    templatefile("${path.module}/helm-values/prometheus-values.yaml", {
      environment        = var.environment
      application_name   = var.application_name
      retention_days     = var.monitoring_retention_days
      storage_class      = "gp3"
      storage_size       = var.environment == "production" ? "100Gi" : "20Gi"
    })
  ]
  
  depends_on = [module.eks]
}

# Jaeger for distributed tracing
resource "helm_release" "jaeger" {
  name       = "jaeger"
  repository = "https://jaegertracing.github.io/helm-charts"
  chart      = "jaeger"
  namespace  = "monitoring"
  version    = "0.71.2"
  
  create_namespace = true
  
  values = [
    templatefile("${path.module}/helm-values/jaeger-values.yaml", {
      environment      = var.environment
      application_name = var.application_name
      storage_class    = "gp3"
    })
  ]
  
  depends_on = [module.eks]
}

# ============================================================================
# SECURITY AND COMPLIANCE
# ============================================================================

# AWS Config for compliance monitoring
resource "aws_config_configuration_recorder" "main" {
  count    = var.environment == "production" ? 1 : 0
  name     = "${var.application_name}-${var.environment}"
  role_arn = aws_iam_role.config[0].arn
  
  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "main" {
  count          = var.environment == "production" ? 1 : 0
  name           = "${var.application_name}-${var.environment}"
  s3_bucket_name = aws_s3_bucket.config[0].bucket
}

resource "aws_s3_bucket" "config" {
  count  = var.environment == "production" ? 1 : 0
  bucket = "${var.application_name}-${var.environment}-config-${random_id.bucket_suffix.hex}"
  
  tags = local.common_tags
}

# GuardDuty for threat detection
resource "aws_guardduty_detector" "main" {
  count  = var.environment == "production" ? 1 : 0
  enable = true
  
  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }
  
  tags = local.common_tags
}

# ============================================================================
# DISASTER RECOVERY
# ============================================================================

# Cross-region backup for production
resource "aws_backup_vault" "main" {
  count       = var.enable_disaster_recovery ? 1 : 0
  name        = "${var.application_name}-${var.environment}-backup"
  kms_key_arn = aws_kms_key.backup[0].arn
  
  tags = local.common_tags
}

resource "aws_backup_plan" "main" {
  count = var.enable_disaster_recovery ? 1 : 0
  name  = "${var.application_name}-${var.environment}-backup"
  
  rule {
    rule_name         = "daily_backup"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = "cron(0 5 ? * * *)"
    
    lifecycle {
      cold_storage_after = 30
      delete_after       = var.backup_retention_days
    }
    
    recovery_point_tags = local.common_tags
  }
  
  tags = local.common_tags
}

resource "aws_kms_key" "backup" {
  count       = var.enable_disaster_recovery ? 1 : 0
  description = "KMS key for backup encryption"
  
  tags = local.common_tags
}

# ============================================================================
# IAM ROLES AND POLICIES
# ============================================================================

# RDS Enhanced Monitoring Role
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "${var.application_name}-${var.environment}-rds-monitoring"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# AWS Config Role
resource "aws_iam_role" "config" {
  count = var.environment == "production" ? 1 : 0
  name  = "${var.application_name}-${var.environment}-config"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "config" {
  count      = var.environment == "production" ? 1 : 0
  role       = aws_iam_role.config[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/ConfigRole"
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.redis.endpoint
  sensitive   = true
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.dns_name
}

output "s3_assets_bucket" {
  description = "S3 assets bucket name"
  value       = aws_s3_bucket.assets.bucket
}

output "monitoring_namespace" {
  description = "Kubernetes monitoring namespace"
  value       = "monitoring"
}

# ============================================================================
# LOCALS
# ============================================================================

locals {
  common_tags = {
    Environment     = var.environment
    Application     = var.application_name
    ManagedBy      = "terraform"
    Project        = "enterprise-cicd"
    CostCenter     = "engineering"
    Owner          = "platform-team"
    BackupRequired = var.environment == "production" ? "true" : "false"
  }
}

