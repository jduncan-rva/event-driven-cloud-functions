#! /usr/bin/env bash

source envars
gcloud config set compute/region $REGION

gsutil -m rm -r gs://$DATA_IN_BKT/
gsutil -m rm -r gs://$DATA_OUT_BKT/
gsutil -m rm -r gs://$VIDEO_IN_BKT/
gsutil -m rm -r gs://$VIDEO_OUT_BKT/

gcloud functions delete $VIDEO_FUNC -q
gcloud functions delete $DECOMPRESS_FUNC -q
gcloud functions delete $REGION $INGEST_FUNC -q