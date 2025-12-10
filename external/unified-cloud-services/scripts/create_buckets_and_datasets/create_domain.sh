#!/bin/bash
# Create Domain Infrastructure - High-Level Wrapper
#
# Creates GCS buckets and BigQuery datasets for a specific domain.
# Useful for ad-hoc infrastructure creation and integration into service examples.
#
# Usage:
#   ./create_domain.sh <domain_name>
#
# Domains: instruments, market_data, features, strategy, execution, ml_models

set -e

if [ -z "$1" ]; then
    echo "❌ Error: Domain name required"
    echo "Usage: $0 <domain_name>"
    echo "Domains: instruments, market_data, features, strategy, execution, ml_models"
    exit 1
fi

DOMAIN=$1
PROJECT_ID="${GCP_PROJECT_ID:-central-element-323112}"
REGION="${GCS_REGION:-asia-northeast1}"

# Domain configuration
case $DOMAIN in
    instruments)
        BUCKET="${INSTRUMENTS_GCS_BUCKET:-instruments-store}"
        TEST_BUCKET="${INSTRUMENTS_GCS_BUCKET_TEST:-instruments-store-test}"
        DATASET="${INSTRUMENTS_BIGQUERY_DATASET:-instruments}"
        ;;
    market_data)
        BUCKET="${MARKET_DATA_GCS_BUCKET:-market-data-tick}"
        TEST_BUCKET="${MARKET_DATA_GCS_BUCKET_TEST:-market-data-tick-test}"
        DATASET="${MARKET_DATA_BIGQUERY_DATASET:-market_data_hft}"
        ;;
    features)
        BUCKET="${FEATURES_GCS_BUCKET:-features-store}"
        TEST_BUCKET="${FEATURES_GCS_BUCKET_TEST:-features-store-test}"
        DATASET="${FEATURES_BIGQUERY_DATASET:-features_data}"
        ;;
    volatility_features)
        BUCKET="${FEATURES_GCS_BUCKET:-features-store}"
        TEST_BUCKET="${FEATURES_GCS_BUCKET_TEST:-features-store-test}"
        DATASET="${VOLATILITY_FEATURES_BIGQUERY_DATASET:-volatility_features}"
        ;;
    onchain_features)
        BUCKET="${FEATURES_GCS_BUCKET:-features-store}"
        TEST_BUCKET="${FEATURES_GCS_BUCKET_TEST:-features-store-test}"
        DATASET="${ONCHAIN_FEATURES_BIGQUERY_DATASET:-onchain_features}"
        ;;
    calendar_features)
        BUCKET="${FEATURES_GCS_BUCKET:-features-store}"
        TEST_BUCKET="${FEATURES_GCS_BUCKET_TEST:-features-store-test}"
        DATASET="${CALENDAR_FEATURES_BIGQUERY_DATASET:-calendar_features}"
        ;;
    strategy)
        BUCKET="${STRATEGY_GCS_BUCKET:-strategy-store}"
        TEST_BUCKET="${STRATEGY_GCS_BUCKET_TEST:-strategy-store-test}"
        DATASET="${STRATEGY_BIGQUERY_DATASET:-strategy}"
        ;;
    execution)
        BUCKET="${EXECUTION_GCS_BUCKET:-execution-store}"
        TEST_BUCKET="${EXECUTION_GCS_BUCKET_TEST:-execution-store-test}"
        DATASET="${EXECUTION_BIGQUERY_DATASET:-execution}"
        ;;
    ml_models)
        BUCKET="${ML_MODELS_GCS_BUCKET:-ml-models-store}"
        TEST_BUCKET="${ML_MODELS_GCS_BUCKET_TEST:-ml-models-store-test}"
        DATASET="${ML_MODELS_BIGQUERY_DATASET:-ml_predictions}"
        ;;
    *)
        echo "❌ Error: Unknown domain '$DOMAIN'"
        echo "Valid domains: instruments, market_data, features, volatility_features, onchain_features, calendar_features, strategy, execution, ml_models"
        exit 1
        ;;
esac

echo "🚀 Creating $DOMAIN domain infrastructure..."
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Bucket: $BUCKET"
echo "   Test Bucket: $TEST_BUCKET"
echo "   Dataset: $DATASET"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Set project
echo "📋 Setting GCP project..."
gcloud config set project $PROJECT_ID

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

# Verify
echo ""
echo "✅ Verification:"
echo "   Bucket location:"
gsutil ls -L -b gs://$BUCKET 2>/dev/null | grep "Location constraint" || echo "   ⚠️  Could not verify bucket location"
echo ""
echo "   Dataset location:"
bq show --format=prettyjson $PROJECT_ID:$DATASET 2>/dev/null | grep location || echo "   ⚠️  Could not verify dataset location"
echo ""

echo "🎉 $DOMAIN domain infrastructure created successfully!"
