#!/bin/bash
# Create All Domain Buckets and Datasets
#
# High-level wrapper for creating GCS buckets and BigQuery datasets for all domains.
# Useful for:
# - Initial setup
# - Cross-service quality gates
# - Ad-hoc infrastructure creation
#
# Domains:
# - instruments
# - market_data
# - features
# - strategy
# - execution
# - ml_models

set -e

PROJECT_ID="${GCP_PROJECT_ID:-central-element-323112}"
REGION="${GCS_REGION:-asia-northeast1}"

echo "🚀 Creating all domain infrastructure..."
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Set project
echo "📋 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Function to create bucket and dataset
create_domain_infrastructure() {
    local DOMAIN=$1
    local BUCKET=$2
    local TEST_BUCKET=$3
    local DATASET=$4

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Domain: $DOMAIN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Create production bucket
    echo ""
    echo "🪣 Creating production bucket: $BUCKET"
    if gsutil ls -b gs://$BUCKET &> /dev/null; then
        echo "   ⚠️  Bucket already exists, skipping..."
    else
        gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET
        echo "   ✅ Bucket created"
    fi

    # Create test bucket
    echo ""
    echo "🪣 Creating test bucket: $TEST_BUCKET"
    if gsutil ls -b gs://$TEST_BUCKET &> /dev/null; then
        echo "   ⚠️  Bucket already exists, skipping..."
    else
        gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$TEST_BUCKET
        echo "   ✅ Test bucket created"
    fi

    # Create BigQuery dataset
    echo ""
    echo "📊 Creating BigQuery dataset: $DATASET"
    if bq ls -d $PROJECT_ID:$DATASET &> /dev/null; then
        echo "   ⚠️  Dataset already exists, skipping..."
    else
        bq mk --dataset \
            --location=$REGION \
            --description="$DOMAIN domain data" \
            $PROJECT_ID:$DATASET
        echo "   ✅ Dataset created"
    fi
}

# Create all domains
create_domain_infrastructure \
    "instruments" \
    "instruments-store" \
    "instruments-store-test" \
    "instruments"

create_domain_infrastructure \
    "market_data" \
    "market-data-tick" \
    "market-data-tick-test" \
    "market_data_hft"

create_domain_infrastructure \
    "features" \
    "features-store" \
    "features-store-test" \
    "features_data"

create_domain_infrastructure \
    "volatility_features" \
    "features-store" \
    "features-store-test" \
    "volatility_features"

create_domain_infrastructure \
    "onchain_features" \
    "features-store" \
    "features-store-test" \
    "onchain_features"

create_domain_infrastructure \
    "calendar_features" \
    "features-store" \
    "features-store-test" \
    "calendar_features"

create_domain_infrastructure \
    "strategy" \
    "strategy-store" \
    "strategy-store-test" \
    "strategy"

create_domain_infrastructure \
    "execution" \
    "execution-store" \
    "execution-store-test" \
    "execution"

create_domain_infrastructure \
    "ml_models" \
    "ml-models-store" \
    "ml-models-store-test" \
    "ml_predictions"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 All domain infrastructure created successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Next steps:"
echo "   1. Update .env files with domain-specific bucket/dataset names"
echo "   2. Update IAM permissions for service accounts"
echo "   3. Run quality gates to verify infrastructure"
