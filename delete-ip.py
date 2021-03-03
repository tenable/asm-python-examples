#!/usr/bin/python3
import sys
from argparse import ArgumentParser
from typing import Dict, Any, Optional, List
from bitdiscovery.api import BitDiscoveryApi, try_multiple_times, get_lastid

parser = ArgumentParser(description="Delete source or IP from inventory")
parser.add_argument('apikey', metavar="APIKEY", type=str, help="Your Bit Discovery API key.")
parser.add_argument('type', metavar="TYPE", type=str, choices=['ip', 'source'], help="The type of the item to delete.")
parser.add_argument('value', metavar="IP/SOURCE", type=str, help="The IP or source to be deleted.")
parser.add_argument('--env', choices=['dev', 'staging', 'prod'], default="dev",
                    help="The Bit Discovery environment (by default 'dev')")
parser.add_argument('--offset', type=int, default=0, help="Offset to the API request data (by default 0).")
parser.add_argument('--limit', type=int, default=5000, help="Limit to the API request data (by default 500).")
args = parser.parse_args()

APIKEY: str = args.apikey
APIURL: str = "https://bitdiscovery.com/api/1.0"
OFFSET: int = args.offset
LIMIT: int = args.limit
IP_TYPE: str = args.type
VALUE: str = args.value

print("Initializing and pulling assets from Bit Discovery...")

api = BitDiscoveryApi(APIURL, APIKEY)
inventories_json: Dict[str, Any] = {}
try:
    inventories_json = api.find_inventories(OFFSET, LIMIT)
except:
    print("API call failed. Try again later.")
    exit(1)

# TODO: maybe remove iteration if we cannot delete from multiple inventories
inventories: Dict[str, str] = {inventories_json['actualInventory']['inventory_name']: APIKEY}

for entityname in inventories:
    jsondata: List[Dict[str, Any]] = []

    deletednum = 0
    if IP_TYPE == 'ip':
        print("Starting inventory: " + str(entityname) + ".")

        # Collect the IP addresses from Bit Discovery inventory with pagination
        lastid: str = ''
        offset: int = OFFSET
        while True:
            result: Optional[Dict[str, Any]] = try_multiple_times(
                lambda: api.search_for_ip_address(LIMIT, lastid, VALUE),
                max_tries=5
            )

            if result is None:
                print("\tAPI call failed too many times. Try again later.")
                exit(1)

            # Append to results list if successfully found
            jsondata.append(result)
            lastid = get_lastid(result)
            offset += LIMIT
            total: int = int(jsondata[0]['total'])

            if offset < total:
                print("\t\t{0:.0%} complete.".format(offset / float(total)))
            else:
                # Exit when the total is reached
                break

        # Iterate over the returned assets and remove the matching assets
        for assets in jsondata:
            for asset in assets.get("assets", []):
                if 'bd.ip_address' in asset and str(asset['bd.ip_address']) == VALUE:
                    # Try to call to IP archivation API endpoint
                    result: Optional[bool] = try_multiple_times(
                        lambda: api.archive_ip(asset['id']),
                        max_tries=5
                    )

                    if result is None:
                        print("\tAPI call failed too many times. Try again later.")
                        exit(1)

                    # Increment deleted count
                    deletednum += 1

    # TODO: shouldn't we "else" here?

    print("Starting sources for: " + str(entityname) + ".")

    sourcesdata: List[Dict[str, Any]] = []

    # Collect the sources from Bit Discovery inventory with pagination
    lastid: str = ''
    offset: int = OFFSET
    while True:
        result: Optional[Dict[str, Any]] = try_multiple_times(
            lambda: api.search_for_source(LIMIT, lastid, VALUE),
            max_tries=5
        )

        if result is None:
            print("\tAPI call failed too many times. Try again later.")
            exit(1)

        # Append to sources list if successfully found
        sourcesdata.append(result)
        lastid = get_lastid(result)
        offset += LIMIT
        total: int = int(sourcesdata[0]['total'])
        if offset < total:
            print("\t\t{} complete.".format('{0:.0%}'.format(offset / float(total))))
        else:
            # Exit when the total is reached
            break

    # Iterate over the sources and remove all matching values
    for sources in sourcesdata:
        for source in sources.get('searches', []):
            if 'keyword' in source and str(source['keyword']).lower() == VALUE:
                # Try to call to source delete API endpoint
                result: Optional[bool] = try_multiple_times(
                    lambda: api.delete_source(str(source['id'])),
                    max_tries=5
                )

                if result is None:
                    print("\tAPI call failed too many times. Try again later.")
                    exit(1)

                # Increment deleted count
                deletednum += 1

    print("\tDeleted a total of " + str(deletednum) + " IPs.")
