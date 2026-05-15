#!/bin/sh
set -e

mkdir -p /data /data/reports /data/charts /tmp/reports /tmp/charts

# Use EC2 instance profile or mounted ~/.aws credentials (same as AWS CLI)
export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"

cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
