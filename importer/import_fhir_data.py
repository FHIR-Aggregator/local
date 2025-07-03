import argparse
import json
import os
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

FHIR_SERVER_URL = os.environ.get("FHIR_SERVER_URL", "http://fhir-server:8080/fhir")
BUCKET_BASE = "https://storage.googleapis.com/fhir-aggregator-public"
POLL_INTERVAL = 10  # seconds
MAX_RETRIES = 5
BACKOFF_FACTOR = 2

# Session with retry logic
session = requests.Session()
retries = Retry(
    total=MAX_RETRIES,
    backoff_factor=BACKOFF_FACTOR,
    status_forcelist=[500, 502, 503, 504],
)
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))


def list_ndjson_objects(bucket_base):
    """
    List all .ndjson objects in the given Google Cloud Storage bucket.

    Args:
        bucket_base (str): The base URL of the bucket.

    Returns:
        list: List of dicts with 'url' and 'size' for each .ndjson object.
    """
    bucket_name = bucket_base.split("/")[-1]
    api_url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o"
    params = {"fields": "items(name, size)", "maxResults": 1000}
    ndjson_files = []

    while True:
        resp = requests.get(api_url, params=params)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("items", []):
            if item["name"].endswith(".ndjson"):
                ndjson_files.append({
                    "url": f"{bucket_base}/{item['name']}",
                    "size": int(item["size"])
                })
        if "nextPageToken" in data:
            params["pageToken"] = data["nextPageToken"]
        else:
            break

    return ndjson_files


def discover_datasets():
    """
    Discover available datasets in the bucket.

    Returns:
        dict: Mapping of dataset name to its size and object URLs.
    """
    print("🔍 Discovering datasets...")
    objects = list_ndjson_objects(BUCKET_BASE)
    projects = [
        _["url"].replace(BUCKET_BASE + '/', '') for _ in objects
    ]
    projects = sorted(
        set([_[:_.find('META') + len('META')] for _ in projects])
    )

    dataset_dict = {}
    for project in projects:
        project_objects = [
            _['url'] for _ in objects if project in _['url']
        ]
        size = sum([_['size'] for _ in objects if project in _['url']])
        size = size / (1024 * 1024)  # Convert to MB
        dataset_dict[project] = {'size': size, 'objects': project_objects}

    return dataset_dict


def submit_import(dataset_name, resource_urls):
    """
    Submit a FHIR $import operation for the given dataset.

    Args:
        dataset_name (str): Name of the dataset.
        resource_urls (list): List of resource URLs to import.
    """
    resource_urls = [url for url in resource_urls if url.endswith(".ndjson")]
    if not resource_urls:
        print(f"⚠️  No resources to import for {dataset_name}")
        return

    print(f"\n🚀 Importing {dataset_name} with {len(resource_urls)} resources...")

    payload = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "inputFormat", "valueString": "application/fhir+ndjson"},
            {"name": "inputSource", "valueUri": f"{BUCKET_BASE}/"},
            {
                "name": "storageDetail",
                "part": [
                    {
                        "name": "type",
                        "valueCode": "https"
                    }
                ]
            }
        ],
    }

    valid_urls = []
    for url in resource_urls:
        try:
            head_resp = session.head(url, allow_redirects=True, timeout=10)
            if head_resp.status_code != 200:
                print(
                    f"⚠️  Resource URL does not exist or is inaccessible: "
                    f"{url} (status {head_resp.status_code})"
                )
            else:
                content_type = head_resp.headers.get("Content-Type", "")
                if "json" not in content_type:
                    print(
                        f"❌ Unexpected Content-Type for {url}: {content_type}"
                    )
                    continue
                valid_urls.append(url)
        except Exception as e:
            print(f"⚠️  Error checking URL {url}: {e}")

    if not valid_urls:
        print(f"❌ No valid resources to import for {dataset_name}")
        return

    for url in valid_urls:
        resource_type = url.split("/")[-1].replace(".ndjson", "")
        print(f"📥 Adding resource {resource_type} from {url}")
        payload["parameter"].append(
            {
                "name": "input",
                "part": [
                    {"name": "type", "valueCode": resource_type},
                    {"name": "url", "valueUri": url},
                ],
            }
        )

    headers = {
        "Content-Type": "application/fhir+json",
        "Prefer": "respond-async",
        "X-Upsert-Extistence-Check": "disabled"
    }
    url = f"{FHIR_SERVER_URL}/$import"
    response = session.post(url, headers=headers, json=payload)

    if "Content-Location" not in response.headers:
        print(
            f"❌ Failed to submit import for {dataset_name} - url {url} "
            f"- status_code {response.status_code}"
        )
        print(response.text)
        sys.exit(1)

    status_url = response.headers["Content-Location"]

    print(f"🕒 Import job submitted for {dataset_name} {status_url}")

    poll_import_status(dataset_name, status_url)


def poll_import_status(dataset_name, status_url):
    """
    Poll the import status endpoint until completion or failure.

    Args:
        dataset_name (str): Name of the dataset.
        status_url (str): URL to poll for import status.
    """
    while True:
        response = requests.get(status_url)
        content_type = response.headers.get("Content-Type", "")
        if "json" not in content_type:
            print(
                f"❌ Unexpected Content-Type for {dataset_name}: {content_type}"
            )
            print(f"Response: {response.text}")
            sys.exit(1)
        status_data = response.json()

        if response.status_code == 202:
            print(
                f"⏳ Import in progress for {dataset_name}... "
                f"(202 Accepted) {status_data}"
            )
            time.sleep(POLL_INTERVAL)
            continue

        if response.status_code != 200:
            print(
                f"❌ Import failed for {dataset_name} - status code "
                f"{response.status_code}"
            )
            print(f"Response: {response.text}")
            sys.exit(1)

        if (
            "resourceType" not in status_data or
            status_data["resourceType"] != "OperationOutcome"
        ):
            print(f"⚠️  Unexpected response format for {dataset_name}:")
            print(f"Response: {status_data}")
            sys.exit(1)

        issues = status_data.get("issue", [])
        ok = True
        for issue in issues:
            severity = issue.get("severity", "unknown")
            details = issue.get("details", {}).get("text", "")
            print(f"ℹ️  OperationOutcome ({severity}): {details}")
            ok = ok and (severity != "error")
        if not ok:
            print(json.dumps(status_data, indent=2))
            print(
                f"❌ Import failed for {dataset_name} "
                f"(OperationOutcome received)"
            )
        else:
            if (
                len(issues) == 1 and
                issues[0].get("severity") == "information" and
                "reportMsg" in issues[0].get("diagnostics", "")
            ):
                report = json.loads(issues[0]["diagnostics"])["reportMsg"]
                print(f"ℹ️  Import report for {dataset_name}: {report}")
            else:
                print(json.dumps(status_data, indent=2))
            print(
                f"✅ Import completed for {dataset_name} "
                f"(OperationOutcome received)"
            )
        sys.exit(0)


def main():
    """
    Main entry point for the FHIR Import Automation Script.
    """
    parser = argparse.ArgumentParser(
        description="FHIR Import Automation Script"
    )
    parser.add_argument(
        "command",
        choices=["import", "list"],
        help="Command to run: import datasets or list datasets"
    )
    parser.add_argument(
        "--only",
        type=str,
        help="Import only datasets containing this keyword"
    )
    parser.add_argument(
        "--skip-legacy",
        action="store_true",
        help="Skip R4 legacy datasets"
    )
    args = parser.parse_args()

    datasets = discover_datasets()

    if args.command == "list":
        print("\nAvailable datasets:")
        for dataset in datasets.keys():
            print(
                f"- {dataset} (Size: {datasets[dataset]['size']:.2f} MB)"
            )
        return

    if args.command == "import":
        for dataset, dataset_info in datasets.items():
            urls = dataset_info['objects']
            if args.skip_legacy and dataset.startswith("R4"):
                continue
            if args.only and args.only not in dataset:
                continue
            submit_import(dataset, urls)


if __name__ == "__main__":
    main()
