# GGame Infra Setup

## Background

To build the foundation for game services, I chose Pulumi + GitHub Actions to manage AWS resources. The idea is simple: define infrastructure as Python code with Pulumi, and use GitHub Actions for automated CI/CD deployment — no more clicking around in the AWS console.

## Tech Stack

- **IaC Tool**: Pulumi (Python) — more flexible than Terraform's HCL since it's just Python
- **CI/CD**: GitHub Actions — native integration with GitHub where the code lives
- **Cloud**: AWS
- **Auth**: OIDC — keyless authentication between GitHub Actions and AWS, no long-lived Access Keys

## Setup Steps

### 1. AWS Side

- Created an OIDC Identity Provider so AWS trusts GitHub Actions identity tokens
- Created an IAM Role with a trust policy pointing to the GitHub OIDC Provider
- Set up AWS SSO (IAM Identity Center) for local dev — temporary credentials via browser login, no long-term Access Keys

### 2. Pulumi Project Init

Created the project with `pulumi new aws-python`, which generates:

- `Pulumi.yaml` — project metadata
- `Pulumi.dev.yaml` — dev stack config (region, custom variables)
- `__main__.py` — program entry point
- `requirements.txt` — Python dependencies

### 3. Modular Resource Management

Organized by AWS service, one module per directory:

```
├── __main__.py          # Entry point, imports all modules
├── vpc/                 # VPC, Subnet, IGW, Route Table
├── ec2/                 # EC2 instances
├── security_group/      # Security group rules
├── s3/                  # S3 (reserved)
├── route53/             # DNS (reserved)
```

`__main__.py` only handles assembly. Resource definitions live in their own modules — scales cleanly as the project grows.

### 4. Initial Resources

| Resource | Name | Spec |
|---|---|---|
| VPC | nphunter-game-vpc | 172.16.0.0/26 |
| Public Subnet | Single AZ (us-east-1a) | Auto-assign public IP |
| Internet Gateway | nphunter-game-igw | — |
| Security Group | ggame-security-group | Only my IP allowed on 22/80/443 |
| EC2 | ggame-ec2 | t3.medium (2vCPU/4GB), Amazon Linux 2023 |

### 5. GitHub Actions CI/CD

Configured `.github/workflows/pulumi.yml` with two jobs:

- **On PR** → runs `pulumi preview`, posts results as a PR comment for review
- **On merge to main** → runs `pulumi up`, deploys resources to AWS

Authentication is handled via OIDC — the GitHub Actions runner exchanges an identity token with AWS STS for temporary credentials. No secrets beyond the Role ARN.

### 6. Local Development

- Log in via AWS SSO: `aws sso login --profile nphunter-sso`
- Set the profile: `export AWS_PROFILE=nphunter-sso`
- Run preview locally: `pulumi preview`

## Daily Workflow

1. Write/modify Pulumi code locally
2. Run `pulumi preview` to validate
3. Push to a new branch, create PR
4. GitHub Actions auto-runs preview, posts result to PR
5. Review and merge
6. GitHub Actions auto-runs `pulumi up` to deploy

## GitHub Secrets

| Secret | Purpose |
|---|---|
| `AWS_ROLE_TO_ASSUME` | OIDC IAM Role ARN |
| `PULUMI_ACCESS_TOKEN` | Pulumi Cloud authentication |
