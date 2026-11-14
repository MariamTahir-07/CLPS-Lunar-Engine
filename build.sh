#!/usr/bin/env bash
# Render build script: installs Python deps, provisions Node.js, builds React frontend.
set -o errexit

# 1. Install Python dependencies
pip install -r backend/requirements.txt

# 2. Provision Node.js & npm (not provided in Render's native Python runtime)
NODE_VERSION=20.18.1
curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.gz" | tar -xz -C /tmp
export PATH="/tmp/node-v${NODE_VERSION}-linux-x64/bin:$PATH"
node -v
npm -v

# 3. Install frontend dependencies and build React production bundle
cd frontend
npm ci
npm run build
