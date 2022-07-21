from __future__ import annotations

import argparse
import csv
from enum import Enum
import ipaddress
import operator
from sortedcontainers import SortedList
import time
from typing import List, Sequence

from bitdiscovery.api import BitDiscoveryApi, try_multiple_times

# max time to wait for the API to update based on loaded ip_range
# after which the next ip_range will be added, this is throttling behavior.
MAX_WAIT_TIME = 7200

ZERO_IP_ADDRESS = ipaddress.ip_address(0)
LOC_DB_PATH: str = ("ip2loc/IP2LOCATION-LITE-DB3.IPV6.CSV",)
APIURL = "https://asm-demo.cloud.tenable.com/api/1.0"


class FILTER_CRITERIA(Enum):
    ANY = 'ANY'
    COUNTRY_CODE = 'COUNTRY_CODE'
    COUNTRY_NAME = 'COUNTRY_NAME'
    REGION = 'REGION'
    CITY = 'CITY'

    def __str__(self):
        return self.value

    def __int__(self):
        return ['PLACEHOLDER', 'ANY', 'COUNTRY_CODE', 'COUNTRY_NAME', 'REGION', 'CITY'].index(self.value)


def filter_row(row: List(str), filters: dict[FILTER_CRITERIA, str]) -> bool:

    if FILTER_CRITERIA.ANY.value in filters.keys() and filters[FILTER_CRITERIA.ANY.value].upper() in map(str.upper, row):
        return True

    for filter, argument in filters.items():
        if filter == FILTER_CRITERIA.ANY:
            pass
        if row[int(FILTER_CRITERIA(filter))].upper() != argument.upper():
            return False
    return True


def sort_input(row: str, ipv4_only: bool) -> None:
    start, end, *rest = row

    try:
        start = int(start)
        end = int(end)
    except:
        raise

    if ipaddress.ip_address(start).ipv4_mapped:
        start = int(ipaddress.ip_address(start).ipv4_mapped)
        end = int(ipaddress.ip_address(end).ipv4_mapped)

    if ipv4_only and 6 == ipaddress.ip_address(start).version:
        return

    global ip_ranges
    ip_ranges.add((start, end))


class filterValue(argparse.Action):
    # Constructor calling
    def __call__(self, parser, namespace,
                 values, option_string=None):
        if not getattr(namespace, self.dest):
            setattr(namespace, self.dest, dict())
        for value in values:
            # split it into key and value
            key, value = value.split('=')
            # assign into dictionary
            if key in FILTER_CRITERIA._member_names_:
                getattr(namespace, self.dest)[key] = value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        "Get IP ranges by geography and optionally add to ASM inventory")

    parser.add_argument("-4", "--ipv4_only",
                        action="store_true", default=False, help="Do not report IPv6 addresses")
    parser.add_argument("--add-to-inventory", action="store_true",
                        default=False, help="Required to add sources to inventory")
    parser.add_argument('--apikey', metavar="APIKEY", type=str,
                        help="Your Bit Discovery API key. Must be for a single inventory")
    parser.add_argument('-f', '--filter',
                        nargs='*',
                        action=filterValue,
                        help=f"Multiple Key=Value criteria where Key is in {FILTER_CRITERIA._member_names_}",
                        )
    args = parser.parse_args(argv)

    print(args)

    assert(bool(args.add_to_inventory) == bool(args.apikey))

    retv = 0
    global ip_ranges
    ip_ranges = SortedList(key=operator.itemgetter(0))
    for file in LOC_DB_PATH:

        with open(file, newline="") as f:
            reader = csv.reader(f, delimiter=",", quotechar='"')
            for row in reader:
                if filter_row(row, args.filter):
                    sort_input(row, args.ipv4_only)

    # apply interval merge algorithm on sorted input
    if not ip_ranges:
        return retv

    resa = []
    resa.append(ip_ranges[0])
    for i in range(len(ip_ranges)):

        if ip_ranges[i][0] <= resa[-1][1]+1:
            resa[-1] = (resa[-1][0], max(ip_ranges[i][1], resa[-1][1]))
        else:
            resa.append(ip_ranges[i])

    api = None
    if args.add_to_inventory:
        api = BitDiscoveryApi(APIURL, args.apikey)
        inventories = api.find_inventories(0, 0)

        assert(inventories['code'] == 400)
        assert(inventories['message'] ==
               'Your API access is limited to a single inventory.')

    for i, (start, end) in enumerate(resa):
        ip_range = f"{str(ipaddress.ip_address(start))}-{str(ipaddress.ip_address(end))}"
        if args.add_to_inventory:

            result = try_multiple_times(
                lambda: api.add_ip(ip_range),
                max_tries=5
            )
            if result is None:
                print(f"API call failed too many times for {ip_range}")

            elapsed_wait, backoff_delay = 0, 1  # 1 second

            while elapsed_wait < MAX_WAIT_TIME \
                    and api.search_for_source(0, 0, ip_range)['searches'][0]['dbdata'] == None:
                # backoff, blocking wait for API to consume the ip range source
                print(f'{ip_range}: max wait time remaining: {MAX_WAIT_TIME - elapsed_wait} s')
                time.sleep(backoff_delay)
                elapsed_wait += backoff_delay
                backoff_delay = min(514, backoff_delay << 1)

        else:
            print(
                f'{i:20}    {ip_range}')

    return retv


if __name__ == "__main__":
    raise SystemExit(main())
