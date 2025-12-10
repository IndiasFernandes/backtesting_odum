#!/bin/bash
# Create Features Domain GCS Bucket and BigQuery Datasets
#
# Creates the features domain infrastructure:
# - GCS bucket: features-store (production)
# - GCS bucket: features-store-test (test)
# - BigQuery datasets: features_data, volatility_features, onchain_features, calendar_features
#
# Region: asia-northeast1
# Services: features-delta-one-service, features-volatility-service, features-onchain-service, calendar-features-service

set -e

PROJECT_ID="${GCP_PROJECT_ID:-central-element-323112}"
REGION="${GCS_REGION:-asia-northeast1}"
BUCKET_NAME="${FEATURES_GCS_BUCKET:-features-store}"
TEST_BUCKET_NAME="${FEATURES_GCS_BUCKET_TEST:-features-store-test}"
DATASETS=("features_data" "volatility_features" "onchain_features" "calendar_features")

echo "🚀 Creating features domain infrastructure..."
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Bucket: $BUCKET_NAME"
echo "   Test Bucket: $TEST_BUCKET_NAME"
echo "   Datasets: ${DATASETS[*]}"
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

# Create BigQuery datasets
echo ""
echo "📊 Creating BigQuery datasets..."
for DATASET_NAME in "${DATASETS[@]}"; do
    echo "   Creating dataset: $DATASET_NAME"
    if bq ls -d $PROJECT_ID:$DATASET_NAME &> /dev/null; then
        echo "      ⚠️  Dataset already exists, skipping..."
    else
        bq mk --dataset \
            --location=$REGION \
            --description="Features domain - $DATASET_NAME" \
            $PROJECT_ID:$DATASET_NAME
        echo "      ✅ Dataset created"
    fi
done

# Verify
echo ""
echo "✅ Verification:"
echo "   Bucket location:"
gsutil ls -L -b gs://$BUCKET_NAME 2>/dev/null | grep "Location constraint" || echo "   ⚠️  Could not verify bucket location"
echo ""
echo "   Dataset locations:"
for DATASET_NAME in "${DATASETS[@]}"; do
    bq show --format=prettyjson $PROJECT_ID:$DATASET_NAME 2>/dev/null | grep location || echo "   ⚠️  Could not verify dataset location for $DATASET_NAME"
done
echo ""

echo "🎉 Features domain infrastructure created successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. Update .env files with:"
echo "      FEATURES_GCS_BUCKET=$BUCKET_NAME"
echo "      FEATURES_GCS_BUCKET_TEST=$TEST_BUCKET_NAME"
echo "      FEATURES_BIGQUERY_DATASET=features_data"
echo "      VOLATILITY_FEATURES_BIGQUERY_DATASET=volatility_features"
echo "      ONCHAIN_FEATURES_BIGQUERY_DATASET=onchain_features"
echo "      CALENDAR_FEATURES_BIGQUERY_DATASET=calendar_features"
echo "      BIGQUERY_LOCATION=$REGION"
echo ""
echo "   2. Update IAM permissions for service accounts"
