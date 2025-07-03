#!/bin/bash

# 🪲 HAPI import job failed due to incorrect Content-Type for ndjson files.
#  "diagnostics": "Job is in FAILED state with 4 error count. Last error: Too many errors: 4. Last error msg was Received content type \"application/octet-stream\" from URL: https://storage.googleapis.com/fhir-aggregator-public/IG/META/SearchParameter-patient-extensions-Patient-age.ndjson. This format is not one of the supported content type: application/ndjson, application/fhir+ndjson, application/json+fhir, application/fhir+json, application/json, text/plain"

# ⚠️ Requirements
#You must have gsutil installed and authenticated with appropriate permissions.
#The bucket must be accessible to your authenticated account.
#This script only affects files ending with .ndjson.


BUCKET="gs://fhir-aggregator-public"

echo "Updating Content-Type to application/fhir+ndjson for all *.ndjson objects in $BUCKET ..."

# List all objects ending with .ndjson
gsutil ls -r "${BUCKET}/**" | grep '\.ndjson$' | while read -r object; do
  echo "Setting Content-Type for: $object"
  gsutil setmeta -h "Content-Type:application/fhir+ndjson" "$object"
done

echo "✅ Metadata update complete."

