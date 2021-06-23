#! /usr/bin/env bash
#A simple script to enable the needed APIs for this demo and to create the properly named GCS buckets
#
#Assumption: This is executed by an authenticated GCP account with the proper project enabled

source envars

enable_apis () {
  echo "Ensuring Proper APIs are enabled. This may take a 2-3 minutes"
  
  gcloud config set compute/region $REGION
  gcloud services enable dataflow.googleapis.com
  gcloud services enable cloudbuild.googleapis.com 
  gcloud services enable cloudfunctions.googleapis.com
  gcloud services enable transcoder.googleapis.com
  gcloud services enable storage-api.googleapis.com
  gcloud services enable storage-component.googleapis.com
  gcloud services enable firestore.googleapis.com
}

create_storage_buckets () {
  echo "Creating Storgae Buckets for Data Files and Videos"

  gsutil mb gs://$DATA_IN_BKT
  gsutil mb gs://$DATA_OUT_BKT
  gsutil mb gs://$VIDEO_IN_BKT
  gsutil mb gs://$VIDEO_OUT_BKT
}

deploy_functions () {

  gcloud functions deploy --source functions/ $VIDEO_FUNC \
    --runtime python37 \
    --trigger-resource gs://$VIDEO_IN_BKT \
    --trigger-event google.storage.object.finalize \
    --set-env-vars VIDEO_OUT_BKT=$VIDEO_OUT_BKT

  gcloud functions deploy --source functions/ $DECOMPRESS_FUNC \
    --runtime python37 \
    --trigger-resource gs://$DATA_IN_BKT \
    --trigger-event google.storage.object.finalize \
    --timeout 360s \
    --set-env-vars DATA_OUT_BKT=$DATA_OUT_BKT,REGION=$REGION,PROJECT_ID=$PROJECT_ID

  gcloud functions deploy --source functions/ $INGEST_FUNC \
    --runtime python37 \
    --trigger-resource gs://$DATA_OUT_BKT \
    --trigger-event google.storage.object.finalize \
    --set-env-vars DATA_OUT_BKT=$DATA_OUT_BKT 
}

enable_apis
create_storage_buckets
deploy_functions
