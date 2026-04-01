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
├── ec2/                 # EC2 instance, IAM role, user_data provisioning
├── security_group/      # Security group rules
├── s3/                  # Artifact bucket for CI/CD deployments
├── iam/                 # GitHub Actions OIDC roles for CI/CD
├── route53/             # DNS — A records for nphunter.net and ggame.nphunter.net
```

`__main__.py` only handles assembly. Resource definitions live in their own modules — scales cleanly as the project grows.

### 4. Resources

| Resource | Name | Spec |
|---|---|---|
| VPC | nphunter-game-vpc | 172.16.0.0/26 |
| Public Subnet | Single AZ (us-east-1a) | — |
| Internet Gateway | nphunter-game-igw | — |
| Security Group | ggame-security-group | SSH from my IP only; HTTP/HTTPS open to internet |
| EC2 | ggame-ec2 | t3.medium (2vCPU/4GB), Amazon Linux 2023 |
| Elastic IP | ggame-eip | Static IP attached to EC2 |
| S3 Bucket | ggame-artifacts | Versioned, 30-day lifecycle expiry |
| Route53 Zone | nphunter.net | Managed hosted zone |
| Route53 A Record | ggame.nphunter.net → EIP | TTL 300 |
| Route53 A Record | nphunter.net → EIP | TTL 300 |
| IAM Role | ggame-ec2-role | EC2 instance role for S3 read + Route53 (certbot) |
| IAM Role | github-actions-ggame-deploy | OIDC role for ggame repo CI to push artifacts to S3 |

### 5. EC2 Provisioning (user_data)

The EC2 instance is automatically configured on first boot via `user_data`:

1. **Nginx** — installs and configures nginx to serve the Godot web export from `/var/www/darkpath`
   - Sets `Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy` headers (required by Godot's SharedArrayBuffer usage)
   - Serves both `ggame.nphunter.net` (game) and `nphunter.net` (landing page)
2. **HTTPS via Certbot** — uses the Route53 DNS-01 challenge plugin to obtain a Let's Encrypt certificate (no inbound port 80 needed for validation)
   - Configures SSL nginx server blocks for both domains
   - Enables `certbot-renew.timer` for automatic certificate renewal
3. **S3 Deploy Timer** — a systemd timer runs every 60 seconds, checking for new artifacts in `s3://ggame-artifacts/web/` and deploying them to the web root

### 6. Artifact Pipeline (CI/CD → S3 → EC2)

The game repo (`illidan53/ggame`) has its own GitHub Actions workflow that:

1. Builds the Godot web export
2. Uploads the zip to `s3://ggame-artifacts/web/` using the `github-actions-ggame-deploy` OIDC role
3. The EC2 systemd timer picks up the new artifact and deploys it automatically

This decouples the game build pipeline from the infra pipeline — each repo only touches its own concerns.

### 7. GitHub Actions CI/CD (Infra)

Configured `.github/workflows/pulumi.yml`:

- **On push to main** → runs `pulumi up`, deploys resources to AWS

Authentication is handled via OIDC — the GitHub Actions runner exchanges an identity token with AWS STS for temporary credentials. No secrets beyond the Role ARN.

### 8. Local Development

- Log in via AWS SSO: `aws sso login --profile nphunter-sso`
- Set the profile: `export AWS_PROFILE=nphunter-sso`
- Run preview locally: `pulumi preview`

## Daily Workflow

1. Write/modify Pulumi code locally
2. Run `pulumi preview` to validate
3. Push to main (or create PR for review)
4. GitHub Actions auto-runs `pulumi up` to deploy

## GitHub Secrets

| Secret | Purpose |
|---|---|
| `AWS_ROLE_TO_ASSUME` | OIDC IAM Role ARN |
| `PULUMI_ACCESS_TOKEN` | Pulumi Cloud authentication |
