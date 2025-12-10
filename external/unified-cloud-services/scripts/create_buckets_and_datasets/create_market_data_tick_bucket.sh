#!/bin/bash
# Create Market Data Domain GCS Bucket and BigQuery Dataset
#
# Creates the market_data domain infrastructure:
# - GCS bucket: market-data-tick (production)
# - GCS bucket: market-data-tick-test (test)
# - BigQuery dataset: market_data_hft
#
# Region: asia-northeast1
# Note: Bucket already exists, script checks existence and skips creation

set -e

PROJECT_ID="${GCP_PROJECT_ID:-central-element-323112}"
REGION="${GCS_REGION:-asia-northeast1}"
BUCKET_NAME="${MARKET_DATA_GCS_BUCKET:-market-data-tick}"
TEST_BUCKET_NAME="${MARKET_DATA_GCS_BUCKET_TEST:-market-data-tick-test}"
DATASET_NAME="${MARKET_DATA_BIGQUERY_DATASET:-market_data_hft}"

echo "🚀 Creating market_data domain infrastructure..."
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Bucket: $BUCKET_NAME"
echo "   Test Bucket: $TEST_BUCKET_NAME"
echo "   Dataset: $DATASET_NAME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Check if gsutil is installed
if ! command -v gsutil &> /dev/null; then
    echo "❌ Error: gsutil not found. Please install Google Cloud SDK."
    exit 1
fi

# Check if bq is installed
if ! command -v bq &> /dev/null; then
    echo "❌ Error: bq CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Set project
echo "📋 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Create production bucket
echo ""
echo "🪣 Creating production bucket: $BUCKET_NAME"
if gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
    echo "   ⚠️  Bucket already exists, skipping..."
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME
    echo "   ✅ Bucket created"
fi

# Create test bucket
echo ""
echo "🪣 Creating test bucket: $TEST_BUCKET_NAME"
if gsutil ls -b gs://$TEST_BUCKET_NAME &> /dev/null; then
    echo "   ⚠️  Bucket already exists, skipping..."
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$TEST_BUCKET_NAME
    echo "   ✅ Test bucket created"
fi

# Create BigQuery dataset
echo ""
echo "📊 Creating BigQuery dataset: $DATASET_NAME"
if bq ls -d $PROJECT_ID:$DATASET_NAME &> /dev/null; then
    echo "   ⚠️  Dataset already exists, skipping..."
else
    bq mk --dataset \
        --location=$REGION \
        --description="Market data domain - raw ticks and candles" \
        $PROJECT_ID:$DATASET_NAME
    echo "   ✅ Dataset created"
fi

# Verify
echo ""
echo "✅ Verification:"
echo "   Bucket location:"
gsutil ls -L -b gs://$BUCKET_NAME 2>/dev/null | grep "Location constraint" || echo "   ⚠️  Could not verify bucket location"
echo ""
echo "   Dataset location:"
bq show --format=prettyjson $PROJECT_ID:$DATASET_NAME 2>/dev/null | grep location || echo "   ⚠️  Could not verify dataset location"
echo ""

echo "🎉 Market data domain infrastructure verified/created successfully!"
echo ""
echo "📝 Environment variables:"
echo "   MARKET_DATA_GCS_BUCKET=$BUCKET_NAME"
echo "   MARKET_DATA_GCS_BUCKET_TEST=$TEST_BUCKET_NAME"
echo "   MARKET_DATA_BIGQUERY_DATASET=$DATASET_NAME"
echo "   BIGQUERY_LOCATION=$REGION"
