#!/usr/bin/python3
import sys
from argparse import ArgumentParser
from typing import Dict, Any, Optional, List
from bitdiscovery.api import BitDiscoveryApi, try_multiple_times, get_lastid
from bitdiscovery.cloud import get_provider, remove_matches, CloudProvider, AWSProvider

parser = ArgumentParser(description="Add your cloud provider assets to your Bit Discovery inventory.")
parser.add_argument('cloudprovider', metavar="PROVIDER", type=str, choices=['amazon-ec2', 'google-cloud', 'azure'],
                    help="The cloud provider to add assets from, either amazon-ec2, google-cloud or azure.")
parser.add_argument('apikey', metavar="APIKEY", type=str, help="Your Bit Discovery API key.")
parser.add_argument('--env', choices=['dev', 'staging', 'prod'], default="dev",
                    help="The Bit Discovery environment (by default 'dev')")
parser.add_argument('--offset', type=int, default=0, help="Offset to the API request data (by default 0).")
parser.add_argument('--limit', type=int, default=5000, help="Limit to the API request data (by default 500).")
args = parser.parse_args()

APIKEY: str = args.apikey
CLOUD_PROVIDER: str = args.cloudprovider
APIURL: str = "https://bitdiscovery.com/api/1.0"
OFFSET: int = args.offset
LIMIT: int = args.limit


# Takes two dicts and safely merges them into a copy
def merge_two_dicts(x: Dict, y: Dict) -> Dict:
    z = x.copy()  # start with x's keys and values
    z.update(y)  # modifies z with y's keys and values & returns None
    return z


# Find all IPs belonging in Bit Discovery
print("Initializing and pulling assets from Bit Discovery...")

api = BitDiscoveryApi(APIURL, APIKEY)
inventories_json: Dict[str, Any] = {}
try:
    inventories_json = api.find_inventories(OFFSET, LIMIT)
except:
    print("API call failed. Try again later.")
    exit(1)

# TODO: maybe remove iteration if we cannot add to multiple inventories
inventories: Dict[str, str] = {inventories_json['actualInventory']['inventory_name']: APIKEY}

for entityname in inventories:
    jsondata = []
    # TODO: this is never used, why do we have to keep this (merge_two_dicts too)
    inventoryips = {}

    print(f"Starting sources for: {entityname}.")

    sourcesdata: List[Dict[str, Any]] = []

    # Collect every source from Bit Discovery inventory with pagination
    lastid: str = ''
    offset: int = OFFSET
    while True:
        result: Optional[Dict[str, Any]] = try_multiple_times(
            lambda: api.search_for_source(LIMIT, lastid, ""),
            max_tries=5
        )

        if result is None:
            print("\tAPI call failed too many times. Try again later.")
            exit(1)

        sourcesdata.append(result)
        lastid = get_lastid(result)
        offset += LIMIT
        total: int = int(sourcesdata[0]['total'])

        if offset > total:
            break

    # Collect all source IPs that aren't CIDRs
    sourceips: Dict[str, int] = {}
    for sources in sourcesdata:
        for source in sources.get('searches', []):
            if 'search_type' in source and source['search_type'] == 'iprange':
                ipcandidate = source['keyword'].lower()
                if '-' in ipcandidate or '/' in ipcandidate:
                    continue
                else:
                    # Number 2 indicates it's a source, not an asset
                    sourceips[ipcandidate] = 2

    # TODO: if inventoryips is to be deleted this can be removed as well
    superset: Dict[str, int] = merge_two_dicts(sourceips, inventoryips)
    for ips in superset:
        if ips in sourceips and ips in inventoryips:
            # Number 3 saying the IP address is found in both
            superset[ips] = 3

    # Find all IPs in cloud
    addednum = 0

    provider: CloudProvider = get_provider(CLOUD_PROVIDER)

    # Get provider IP ranges from the provider
    # TODO: why is this read? we don't use this for anything
    print(f"\tWe're on {provider.name}, so processing accordingly")
    print(f"\t\tGetting and parsing all of {provider.name}'s public IP space")
    prefixes: Dict[str, int] = provider.get_ip_ranges()

    # Get your ips from the provider
    print("\t\tGetting and parsing your public IPs")
    ips: Dict[str, int] = provider.get_instance_ips()

    # If IPs in cloud match Bit Discovery remove them from list to do further checks on (they haven't changed)
    print("\t\tIgnorning assets that haven't changed.")
    ips_new, old_ips = remove_matches(superset, inventoryips, sourceips, ips)

    # If IPs are not in Bit Discovery but they are in cloud add them
    print("\t\tAdding new IPs")
    for new_ip in ips_new:
        # Try to add the new IPs to the Bit Discovery inventory
        result: Optional[bool] = try_multiple_times(
            lambda: api.add_ip(new_ip),
            max_tries=5
        )

        if result is None:
            print("\tAPI call failed too many times. Try again later.")
            exit(1)

        # Increment added count
        addednum += 1

    print(f"\tAdded a total of {str(addednum)} {provider.name} IPs.")

    # If provider is AWS, then we can also retrieve the buckets
    if type(provider) == AWSProvider:
        print("\t\tFinding s3 buckets.")
        buckets = AWSProvider().find_s3_buckets()

        print("\t\tAdding s3 buckets.")
        addedbucket = 0
        for bucket in buckets:
            url = AWSProvider().find_s3_region(bucket)

            # Try to add bucket URLs to the Bit Discovery inventory
            success: Optional[bool] = try_multiple_times(
                lambda: api.add_source(url),
                max_tries=5
            )

            if result is None:
                print("\tAPI call failed too many times. Try again later.")
                exit(1)

            # Increment bucket count
            addedbucket += 1

        print("\tAdded a total of " + str(addedbucket) + " S3 buckets.")

print("Done.")
