#!/bin/bash
# Create Market Data Processing Domain GCS Bucket and BigQuery Dataset
#
# Creates the market_data domain infrastructure for processed candles:
# - GCS bucket: market-data-tick (shared with market-tick-data-handler)
# - BigQuery dataset: market_data_hft (shared with market-tick-data-handler)
#
# Region: asia-northeast1
# Note: Uses same bucket/dataset as market-tick-data-handler (same domain)

set -e

PROJECT_ID="${GCP_PROJECT_ID:-central-element-323112}"
REGION="${GCS_REGION:-asia-northeast1}"
BUCKET_NAME="${MARKET_DATA_GCS_BUCKET:-market-data-tick}"
TEST_BUCKET_NAME="${MARKET_DATA_GCS_BUCKET_TEST:-market-data-tick-test}"
DATASET_NAME="${MARKET_DATA_BIGQUERY_DATASET:-market_data_hft}"

echo "🚀 Verifying market_data domain infrastructure for market-data-processing-service..."
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Bucket: $BUCKET_NAME (shared with market-tick-data-handler)"
echo "   Test Bucket: $TEST_BUCKET_NAME"
echo "   Dataset: $DATASET_NAME (shared with market-tick-data-handler)"
echo ""
echo "   ℹ️  Note: Uses same bucket/dataset as market-tick-data-handler (same domain)"
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

# Verify production bucket exists
echo ""
echo "🪣 Verifying production bucket: $BUCKET_NAME"
if gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
    echo "   ✅ Bucket exists"
else
    echo "   ⚠️  Bucket does not exist. Run create_market_data_tick_bucket.sh first."
    exit 1
fi

# Verify test bucket exists
echo ""
echo "🪣 Verifying test bucket: $TEST_BUCKET_NAME"
if gsutil ls -b gs://$TEST_BUCKET_NAME &> /dev/null; then
    echo "   ✅ Test bucket exists"
else
    echo "   ⚠️  Test bucket does not exist. Run create_market_data_tick_bucket.sh first."
    exit 1
fi

# Verify BigQuery dataset exists
echo ""
echo "📊 Verifying BigQuery dataset: $DATASET_NAME"
if bq ls -d $PROJECT_ID:$DATASET_NAME &> /dev/null; then
    echo "   ✅ Dataset exists"
else
    echo "   ⚠️  Dataset does not exist. Run create_market_data_tick_bucket.sh first."
    exit 1
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

echo "🎉 Market data processing service infrastructure verified!"
echo ""
echo "📝 Environment variables (same as market-tick-data-handler):"
echo "   MARKET_DATA_GCS_BUCKET=$BUCKET_NAME"
echo "   MARKET_DATA_GCS_BUCKET_TEST=$TEST_BUCKET_NAME"
echo "   MARKET_DATA_BIGQUERY_DATASET=$DATASET_NAME"
echo "   BIGQUERY_LOCATION=$REGION"
