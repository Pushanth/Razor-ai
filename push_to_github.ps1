# RAZORAI — Push to GitHub Script
# Run this script after creating your repository on GitHub.

param (
    [Parameter(Mandatory=$false)]
    [string]$RepoUrl = ""
)

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "🚀 RAZORAI — GitHub Deployment Assistant" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Initialize Git Repository
if (-not (Test-Path ".git")) {
    Write-Host "[1/4] Initializing Git repository..." -ForegroundColor Yellow
    git init
} else {
    Write-Host "[1/4] Git repository already initialized." -ForegroundColor Green
}

# 2. Stage All Project Files
Write-Host "[2/4] Staging project files..." -ForegroundColor Yellow
git add .

# 3. Commit
Write-Host "[3/4] Committing codebase..." -ForegroundColor Yellow
git commit -m "feat: initial release of RAZORAI — Autonomous Financial Intelligence & Agentic Commerce Platform"

# 4. Check / Add Remote & Push
if ($RepoUrl -ne "") {
    Write-Host "[4/4] Configuring remote and pushing to $RepoUrl..." -ForegroundColor Yellow
    git branch -M main
    git remote remove origin -ErrorAction SilentlyContinue
    git remote add origin $RepoUrl
    git push -u origin main
    Write-Host "`n✅ Successfully pushed RAZORAI to $RepoUrl!" -ForegroundColor Green
} else {
    Write-Host "`n📌 Next Step to push to your GitHub:" -ForegroundColor Yellow
    Write-Host "1. Create a new repository on https://github.com/new"
    Write-Host "2. Run the following commands:" -ForegroundColor White
    Write-Host "   git branch -M main" -ForegroundColor Cyan
    Write-Host "   git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git" -ForegroundColor Cyan
    Write-Host "   git push -u origin main" -ForegroundColor Cyan
}

Write-Host "=================================================================" -ForegroundColor Cyan
