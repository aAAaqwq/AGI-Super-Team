---
name: cicd-pipeline-generator
description: This skill should be used when creating or configuring CI/CD pipeline files for automated testing, building, and deployment. Use this for generating GitHub Actions workflows, GitLab CI configs, CircleCI configs, or other CI/CD platform configurations. Ideal for setting up automated pipelines for Node.js/Next.js applications, including linting, testing, building, and deploying to platforms like Vercel, Netlify, or AWS.
---

# CI/CD Pipeline Generator

## Overview

Generate production-ready CI/CD pipeline configuration files for various platforms (GitHub Actions, GitLab CI, CircleCI, Jenkins). This skill provides templates and guidance for setting up automated workflows that handle linting, testing, building, and deployment for modern web applications, particularly Node.js/Next.js projects.

## Core Capabilities

### 1. Platform Selection

Choose the appropriate CI/CD platform based on project requirements:

- **GitHub Actions**: Best for GitHub-hosted projects with native integration
- **GitLab CI/CD**: Ideal for GitLab repositories with complex pipeline needs
- **CircleCI**: Optimized for Docker workflows and fast build times
- **Jenkins**: Suitable for self-hosted, highly customizable environments

Refer to `references/platform-comparison.md` for detailed platform comparisons, pros/cons, and use case recommendations.

### 2. Pipeline Configuration Generation

Generate pipeline configs following these principles:

#### Pipeline Stages

Structure pipelines with these standard stages:

1. **Install Dependencies**
   - Checkout code from repository
   - Setup runtime environment (Node.js version)
   - Restore cached dependencies
   - Install dependencies with `npm ci`
   - Cache dependencies for future runs

2. **Lint**
   - Run ESLint for code quality
   - Run TypeScript type checking
   - Fail fast on linting errors

3. **Test**
   - Execute unit tests
   - Execute integration tests
   - Generate code coverage reports
   - Upload coverage to reporting services (Codecov, Coveralls)

4. **Build**
   - Create production build
   - Verify build succeeds
   - Store build artifacts

5. **Deploy**
   - Deploy to staging (develop branch)
   - Deploy to production (main branch)
   - Run post-deployment smoke tests

#### Caching Strategy

Implement effective caching to speed up builds:

```yaml
# Cache node_modules based on package-lock.json
cache:
  key: ${{ hashFiles('package-lock.json') }}
  paths:
    - node_modules/
    - .npm/
```

#### Environment Variables

Configure necessary environment variables:
- `NODE_ENV`: Set to `production` for builds
- Platform-specific tokens: Store as secrets
- Build-time variables: Pass to build process

### 3. Template Usage

Use provided templates from `assets/` directory:

**GitHub Actions Template** (`assets/github-actions-nodejs.yml`):
- Multi-job workflow with lint, test, build, deploy
- Matrix builds for multiple Node.js versions (optional)
- Vercel deployment integration
- Artifact uploading
- Code coverage reporting

**GitLab CI Template** (`assets/gitlab-ci-nodejs.yml`):
- Multi-stage pipeline
- Dependency caching
- Manual production deployment
- Automatic staging deployment
- Coverage reporting

To use a template:
1. Copy the appropriate template file
2. Place in the correct location:
   - GitHub Actions: `.github/workflows/ci.yml`
   - GitLab CI: `.gitlab-ci.yml`
3. Customize deployment targets, environment variables, and branch names
4. Add required secrets to platform settings

### 4. Deployment Configuration

#### Vercel Deployment

For GitHub Actions:
```yaml
- uses: amondnet/vercel-action@v25
  with:
    vercel-token: ${{ secrets.VERCEL_TOKEN }}
    vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
    vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
    vercel-args: '--prod'
```

**Required Secrets**:
- `VERCEL_TOKEN`: Get from Vercel account settings
- `VERCEL_ORG_ID`: From Vercel project settings
- `VERCEL_PROJECT_ID`: From Vercel project settings

#### Netlify Deployment

```yaml
- run: |
    npm install -g netlify-cli
    netlify deploy --prod --dir=.next
  env:
    NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
    NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

#### AWS S3 + CloudFront

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-1

- run: |
    aws s3 sync .next/static s3://${{ secrets.S3_BUCKET }}/static
    aws cloudfront create-invalidation --distribution-id ${{ secrets.CF_DIST_ID }} --paths "/*"
```

### 5. Testing Integration

Configure test execution with proper reporting:

**Jest Configuration**:
```yaml
- name: Run tests with coverage
  run: npm test -- --coverage --coverageReporters=text --coverageReporters=lcov

- name: Upload coverage
  uses: codecov/codecov-action@v4
  with:
    files: ./coverage/lcov.info
    flags: unittests
```

**Fail Fast Strategy**:
```yaml
# Run quick tests first
jobs:
  lint:  # Fails in ~30 seconds
  test:  # Fails in ~2 minutes
  build: # Fails in ~5 minutes
    needs: [lint, test]
  deploy:
    needs: [build]
```

### 6. Branch-Based Workflows

Implement different behaviors per branch:

**Feature Branches / PRs**:
- Run lint + test only
- No deployment
- Add PR comments with test results

**Develop Branch**:
- Run lint + test + build
- Deploy to staging environment
- Automatic deployment

**Main Branch**:
- Run lint + test + build
- Deploy to production
- Manual approval (optional)
- Create release tags

**Example**:
```yaml
deploy_staging:
  if: github.ref == 'refs/heads/develop'
  # Deploy to staging

deploy_production:
  if: github.ref == 'refs/heads/main'
  environment: production  # Requires manual approval
  # Deploy to production
```

## Workflow Decision Tree

Follow this decision tree to generate the appropriate pipeline:

1. **Which platform?**
   - GitHub → Use `assets/github-actions-nodejs.yml`
   - GitLab → Use `assets/gitlab-ci-nodejs.yml`
   - CircleCI/Jenkins → Adapt GitHub Actions template
   - Unsure → Consult `references/platform-comparison.md`

2. **What stages are needed?**
   - Always include: Lint, Test, Build
   - Optional: Security scanning, E2E tests, performance tests
   - Add deployment stage if deploying from CI

3. **Which deployment platform?**
   - Vercel → Use Vercel deployment examples
   - Netlify → Use Netlify CLI approach
   - AWS → Use AWS Actions/CLI
   - Custom → Implement custom deployment script

4. **What triggers?**
   - On push to main/develop
   - On pull request
   - On tag creation
   - Manual workflow dispatch

5. **What environment variables needed?**
   - Platform tokens (Vercel, Netlify, AWS)
   - API keys for external services
   - Build-time environment variables
   - Feature flags

## Best Practices

### Security
- Store all secrets in platform secret management (never in code)
- Use least-privilege tokens (read-only when possible)
- Rotate secrets regularly
- Audit secret access permissions
- Never log secrets (use `***` masking)

### Performance
- Cache dependencies aggressively
- Parallelize independent jobs
- Use matrix builds for multi-version testing
- Fail fast: Run quick checks before slow ones
- Optimize Docker layer caching

### Reliability
- Pin exact Node.js versions (`18.x` not just `18`)
- Commit lockfiles (`package-lock.json`)
- Add retry logic for flaky external services
- Set reasonable timeouts (10-15 minutes max)
- Use `continue-on-error` for non-critical steps

### Maintainability
- Add comments explaining complex logic
- Use reusable workflows/templates
- Keep configs DRY (Don't Repeat Yourself)
- Version control all pipeline changes
- Document required secrets in README

## Common Patterns

### Multi-Environment Deployment
```yaml
deploy_staging:
  environment: staging
  if: github.ref == 'refs/heads/develop'

deploy_production:
  environment: production
  if: github.ref == 'refs/heads/main'
  needs: [deploy_staging]
```

### Matrix Testing
```yaml
strategy:
  matrix:
    node-version: [16.x, 18.x, 20.x]
    os: [ubuntu-latest, windows-latest]
```

### Conditional Steps
```yaml
- name: Deploy
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: npm run deploy
```

### Artifact Management
```yaml
- name: Upload build
  uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: .next/
    retention-days: 7

- name: Download build
  uses: actions/download-artifact@v4
  with:
    name: build-output
```

## Troubleshooting

### Pipeline Failures
1. Check action/job logs for error messages
2. Verify environment variables and secrets are set
3. Test commands locally before adding to pipeline
4. Check for platform-specific issues in documentation

### Slow Builds
1. Verify cache is working (check cache hit/miss logs)
2. Parallelize independent jobs
3. Use faster runners if available
4. Optimize dependency installation

### Deployment Failures
1. Verify deployment tokens are valid
2. Check platform status pages
3. Review deployment logs
4. Test deployment commands locally

### Security Scan Failures (GitHub Actions)

**问题**: "Resource not accessible by integration" or "Failed to gather information for telemetry"

**根本原因**: GitHub Actions权限配置不完整

**修复步骤**:

1. **添加workflow级别权限** (可能不够):
```yaml
permissions:
  contents: read
  security-events: write
```

2. **在security job级别添加权限** (必需！):
```yaml
jobs:
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write  # 关键！job级别必须显式声明
    steps:
      - uses: aquasecurity/trivy-action@master
      - uses: github/codeql-action/upload-sarif@v4  # 使用最新版本
```

**关键发现** (老王的实战经验):
- ⚠️ **workflow级别权限不会自动传递到job**
- 必须在上传SARIF结果的job中显式声明`security-events: write`
- 使用最新版本的CodeQL Action（v4）避免弃用警告

**CodeQL版本对比**:
- **v3** (2022): 功能完整，2026年12月弃用
- **v4** (2025): ✅ 最新稳定版，推荐使用

**如果还不行**:
检查GitHub仓库设置：
```
Settings → Actions → General → Workflow permissions
→ 选择 "Read and write permissions"
```

**老王备注**: 2026-02-25实战记录，AutoGeo项目完整修复过程

## Resources

### Templates (`assets/`)
- `github-actions-nodejs.yml`: Complete GitHub Actions workflow
- `gitlab-ci-nodejs.yml`: Complete GitLab CI pipeline

### Reference Documentation (`references/`)
- `platform-comparison.md`: Detailed comparison of CI/CD platforms, deployment targets, best practices, and common patterns

## Example Usage

**User Request**: "Create a GitHub Actions workflow that runs tests and deploys to Vercel"

**Steps**:
1. Copy `assets/github-actions-nodejs.yml` template
2. Create `.github/workflows/` directory if it doesn't exist
3. Save as `.github/workflows/ci.yml`
4. Update deployment section with Vercel credentials
5. Add secrets to GitHub repository settings:
   - `VERCEL_TOKEN`
   - `VERCEL_ORG_ID`
   - `VERCEL_PROJECT_ID`
6. Commit and push to trigger workflow

**User Request**: "Set up GitLab CI with staging and production environments"

**Steps**:
1. Copy `assets/gitlab-ci-nodejs.yml` template
2. Save as `.gitlab-ci.yml` in repository root
3. Configure GitLab CI/CD variables:
   - `VERCEL_TOKEN`
   - Other deployment credentials
4. Review manual approval settings for production
5. Commit to trigger pipeline

## Advanced Configuration

### Monorepo Support
```yaml
paths:
  - 'apps/frontend/**'
  - 'packages/**'
```

### Scheduled Runs
```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
```

### External Service Integration
```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Security Scanning

#### 基础安全扫描（npm audit）
```yaml
- name: Run security audit
  run: npm audit --audit-level=moderate

- name: Check for vulnerabilities
  uses: snyk/actions/node@master
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

#### 完整安全扫描（Gitleaks + Trivy）

**推荐配置**（适用于生产环境）：

```yaml
security:
  name: Security Scan
  runs-on: ubuntu-latest
  permissions:
    contents: read
    security-events: write

  steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # 必须fetch-all才能检测完整Git历史

    # Gitleaks - 密钥泄露检测
    - name: Run Gitleaks
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        # GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}  # 可选：Pro版本

    # Trivy - 依赖漏洞检测
    - name: Run Trivy
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: './backend'
        format: 'sarif'
        output: 'trivy-results.sarif'

    # 上传到GitHub Security
    - name: Upload Trivy results
      uses: github/codeql-action/upload-sarif@v4
      with:
        sarif_file: 'trivy-results.sarif'
      if: always()
```

**Gitleaks配置文件**（`.gitleaks.toml`）：

```toml
title = "Gitleaks配置"

[extend]
useDefault = true  # 使用Gitleaks默认规则

# 自定义规则
[[rules]]
description = "硬编码API密钥"
id = "hardcoded-api-key"
regex = '''(?:api_key|apikey|secret|token|password)\s*=\s*['"][a-zA-Z0-9+/=_]{20,}['"]'''
entropy = 3.5

[[rules]]
description = "GitHub Token"
id = "github-token"
regex = '''gh[pousr]_[a-zA-Z0-9]{36,255}'''
keywords = ["ghp_", "gho_", "ghu_", "ghs_", "ghr_"]

[[rules]]
description = "数据库连接字符串"
id = "database-connection-string"
regex = '''(?i)mysql://[^\s]+|postgres://[^\s]+|mongodb://[^\s]+'''
keywords = ["mysql://", "postgres://", "mongodb://"]

# 允许列表（避免误报）
[allowlist]
paths = [
  '''\.git$''',
  '''node_modules''',
  '''tests/''',     # 测试文件可能包含示例密钥
  '''docs/''',
  '''.env\.example'''
]
```

**Gitleaks vs Trivy对比**：

| 检测工具 | 检测目标 | 典型场景 | 是否必需 |
|---------|---------|---------|---------|
| **Gitleaks** | 代码中的密钥泄露、硬编码密码、API密钥 | 检测开发者误提交的敏感信息 | ✅ 必需 |
| **Trivy** | 依赖包漏洞、系统包CVE、配置错误 | 检测第三方库的安全漏洞 | ✅ 必需 |
| **CodeQL** | 代码逻辑漏洞（SQL注入、XSS等） | 检测代码实现的安全问题 | 推荐 |

**老王的实战建议**（2026-02-25）：

1. **必须同时使用Gitleaks和Trivy**
   - Gitleaks检测"自己写的代码"的问题
   - Trivy检测"用的第三方库"的问题
   - 两者互补，缺一不可

2. **Gitleaks必须fetch完整Git历史**
   ```yaml
   - uses: actions/checkout@v4
     with:
       fetch-depth: 0  # 必须设置！
   ```

3. **权限配置很重要**
   ```yaml
   # Workflow级别
   permissions:
     contents: read
     security-events: write

   # Job级别（必需！）
   security:
     permissions:
       contents: read
       security-events: write
   ```

4. **本地测试Gitleaks**
   ```bash
   # 安装
   brew install gitleaks  # macOS/Linux
   scoop install gitleaks  # Windows

   # 测试
   gitleaks detect --source . --config .gitleaks.toml
   ```

5. **处理密钥泄露的正确流程**
   - 真实密钥：立即撤销并更换
   - 示例数据：使用环境变量
   - 历史泄露：使用git filter-repo清除
