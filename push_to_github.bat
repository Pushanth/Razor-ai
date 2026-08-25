@echo off
echo =================================================================
echo 🚀 RAZORAI — GitHub Deployment Assistant
echo =================================================================

if not exist .git (
    echo [1/4] Initializing Git repository...
    git init
) else (
    echo [1/4] Git repository already initialized.
)

echo [2/4] Staging project files...
git add .

echo [3/4] Committing codebase...
git commit -m "feat: initial release of RAZORAI — Autonomous Financial Intelligence & Agentic Commerce Platform"

echo [4/4] Next Steps:
echo 1. Create a repository on https://github.com/new
echo 2. Replace URL and run:
echo    git branch -M main
echo    git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
echo    git push -u origin main

echo =================================================================
pause
