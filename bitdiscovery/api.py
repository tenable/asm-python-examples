import requests
from typing import Any, Callable, Dict, Optional, List


def try_multiple_times(fn: Callable[..., Any], max_tries: int) -> Optional[Any]:
    """
    Retry a function multiple times if it fails.

    :param fn: The function to run (it should return on success, throw on failure)
    :param max_tries: The number of times after failure is registered, and None returned.
    :return: Either the returned value on success, or None on failure.
    """
    result = None
    i = 0
    while result is None and i < max_tries:
        try:
            result = fn()
        except Exception as e:
            print("ERROR: " + str(e))
            result = None
        i += 1

    return result


def get_lastid(assets: Dict[str, List[Dict[str, str]]]) -> str:
    """
    Finds the last asset's ID so you know where you left off

    :param assets: The list of assets as got back from the API.
    :return: The last asset from the list.
    """
    lastid = ''
    if "assets" in assets:
        for asset in assets["assets"]:
            if "id" in asset:
                lastid = str(asset["id"])
    return lastid


class BitDiscoveryApi:
    """
    Initializes an object to call the Bit Discovery API with a base URL and API key.
    """
    apiurl: str
    apikey: str

    def __init__(self, apiurl: str, apikey: str):
        self.apiurl = apiurl
        self.apikey = apikey

    def find_inventories(self, offset: int, limit: int) -> Dict[str, Any]:
        url = f'{self.apiurl}/inventories/list?offset={str(offset)}&limit={str(limit)}&forcescreenshots=false'
        headers = {'Accept': 'application/json', 'Authorization': self.apikey}
        r = requests.get(url, headers=headers)
        return r.json()

    def get_dashboard(self, querytypes: str) -> Dict[str, Any]:
        url = f'{self.apiurl}/dashboard?columns={str(querytypes)}'
        payload = '[ { "column": "bd.original_hostname", "type": "ends with", "value": "" } ]'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': self.apikey}

        r = requests.post(url, data=payload, headers=headers)
        return r.json()

    def search_inventory(self, limit: int, after: str) -> Dict[str, Any]:
        payload = '[ { "column": "bd.original_hostname", "type": "ends with", "value": "" } ]'

        if after == '':
            url = f'{self.apiurl}/inventory?limit={str(limit)}&offset=0&sortorder=true&inventory=false'
        else:
            url = f'{self.apiurl}/inventory?limit={str(limit)}&after={str(after)}&sortorder=true&inventory=false'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': self.apikey}

        r = requests.post(url, data=payload, headers=headers)
        return r.json()

    def search_for_ip_address(self, limit: int, after: str, ip: str) -> Dict[str, Any]:
        payload = '[ {"column": "bd.ip_address", "type": "is", "value": "' + str(ip) + '" } ]'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': self.apikey}

        if after == '':
            url = f'{self.apiurl}/inventory?limit={limit}&sortorder=true&columns=id,bd.ip_address'
        else:
            url = f'{self.apiurl}/inventory?limit={limit}&after={after}&sortorder=true&columns=id,bd.ip_address'

        r = requests.post(url, data=payload, headers=headers)
        return r.json()

    def search_for_source(self, limit: int, after: str, search: str) -> Dict[str, Any]:
        headers = {'Accept': 'application/json', 'Authorization': self.apikey}

        if after == '':
            url = f'{self.apiurl}/sources?offset=0&limit={limit}&search={search}'
        else:
            url = f'{self.apiurl}/sources?offset=0&offset={after}&limit={limit}&search={search}'

        r = requests.get(url, headers=headers)
        return r.json()

    def add_ip(self, new_ip: str) -> bool:
        payload = '{ "ip": "' + str(new_ip) + '" }'
        url = f'{self.apiurl}/source/ip/add'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': self.apikey}
        requests.post(url, data=payload, headers=headers)
        return True

    def add_source(self, new_source: str) -> bool:
        payload = '{ "keyword": "' + str(new_source) + '" }'
        url = f'{self.apiurl}/source/add?as_subdomain=true&dont_discover=true'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': self.apikey}
        requests.post(url, data=payload, headers=headers)
        return True

    def archive_ip(self, old_id: str) -> bool:
        payload = '[ {"id": "' + old_id + '", "hidden": true } ]'
        url = f'{self.apiurl}/asset/hide'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': self.apikey}
        requests.post(url, data=payload, headers=headers)
        return True

    def delete_source(self, old_source_id: str) -> bool:
        url = f'{self.apiurl}/source/{old_source_id}/delete'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': self.apikey}
        requests.post(url, headers=headers)
        return True
