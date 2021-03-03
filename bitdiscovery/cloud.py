import requests
import json
import urllib.request
from typing import List, Dict, Callable


# Attempts to remove any matches from a super set of all IPs and sources in Bit Discovery that are still correct
def remove_matches(superset: Dict[str, int], bit_discovery_ips: Dict[str, int], bit_discovery_sources: Dict[str, int],
                   cloud_ips: Dict[str, int]) -> (Dict[str, int], Dict[str, int]):
    for theiplist in cloud_ips.copy().items():
        # theiplist is basically just a two column list, and the first is the IP and the second is the source 1,2,3
        ip = theiplist[0]
        if ip in superset:
            if superset[ip] == 1 or superset[ip] == 3:
                del superset[ip]
                del bit_discovery_ips[ip]
                del cloud_ips[ip]
            if superset[ip] == 2 or superset[ip] == 3:
                del superset[ip]
                del bit_discovery_sources[ip]
                del cloud_ips[ip]

    old_ips = {}
    for ip in superset:
        if ip not in cloud_ips:
            old_ips[ip] = 1

    return cloud_ips, old_ips


class CloudProvider:
    """
    Base abstract class to contain the needed fields and methods for every new cloud provider.
    """
    name: str
    sh: Callable

    def get_ip_ranges(self) -> Dict[str, int]:
        """
        Retrieve every IP, range or CIDR that a given cloud provider owns.

        :return: a dictionary with the keys as the IPs.
        """
        prefixes = {}
        return prefixes

    def get_instance_ips(self) -> Dict[str, int]:
        """
        Retrieve every IP of running cloud instances, that the logged in user owns (extracted from CLIs).

        :return: a dictionary with the keys as the IPs.
        """
        ips = {}
        return ips


class AWSProvider(CloudProvider):
    def __init__(self):
        self.name = "AWS"

    def get_ip_ranges(self) -> Dict[str, int]:
        prefixes = {}
        url = 'https://ip-ranges.amazonaws.com/ip-ranges.json'
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
        for ips in data['prefixes']:
            prefixes[ips['ip_prefix']] = 1
        return prefixes

    # Finds all of Amazon's various regions
    def find_aws_regions(self) -> List[str]:
        from sh import aws
        cmd = aws('ec2', 'describe-regions', '--output', 'json')
        regions: Dict[str, List[Dict[str, str]]] = json.loads(str(cmd))
        return [r['RegionName'] for r in regions['Regions']]

    # Gets all of the Elastic (static) IPs from AWS
    def find_aws_elastic_ips(self, region: str) -> Dict[str, int]:
        from sh import aws
        ips: Dict[str, int] = {}
        cmd = aws('ec2', 'describe-addresses', '--region', region, '--output', 'json')
        iplist: Dict[str, List[Dict[str, str]]] = json.loads(str(cmd))
        for addresses in iplist['Addresses']:
            ips[addresses['PublicIp']] = 1
        return ips

    # Gets all of the dynamic IPs from AWS's various regions
    def find_aws_dynamic_ips(self, region: str) -> Dict[str, int]:
        from sh import aws
        ips: Dict[str, int] = {}
        cmd = aws('ec2', 'describe-instances', '--region', region, '--query',
                  'Reservations[*].Instances[*].[PublicIpAddress]', '--output', 'json')
        iplist: List[List[List[str]]] = json.loads(str(cmd))
        # This is required to unravel the list within list within list that AWS responds with
        for innerlist in iplist:
            for theips in innerlist:
                ips[theips[0]] = 1
        return ips

    def get_instance_ips(self) -> Dict[str, int]:
        regions = self.find_aws_regions()
        ips: Dict[str, int] = {}
        for region in regions:
            # First get dynamic IPs
            print("\t\t\t" + str(region))
            ipdict = self.find_aws_dynamic_ips(region)
            for ip in ipdict:
                ips[ip] = 1

            # Then get elastic IPs
            ipdict = self.find_aws_elastic_ips(region)
            for ip in ipdict:
                ips[ip] = 1

        return ips

    def find_s3_buckets(self) -> Dict[str, int]:
        """
        Retrieve all running S3 buckets that the logged-in user owns (extracted from AWS CLI).

        :return: a dictionary with the buckets as keys.
        """
        from sh import aws
        buckets = {}
        cmd = aws('s3api', 'list-buckets', '--query', "Buckets[].Name", '--output', 'json')
        bucketjson: List[str] = json.loads(str(cmd))
        for i in bucketjson:
            buckets[i] = 1
        return buckets

    def find_s3_region(self, bucket: str) -> str:
        """
        Returns the URL for an S3 bucket (extracted from AWS CLI).

        :return: the URL string.
        """
        from sh import aws
        cmd = aws('s3api', 'get-bucket-location', '--bucket', str(bucket), '--output', 'json')
        regs: Dict[str, str] = json.loads(str(cmd))
        return str(bucket) + '.s3.' + str(regs['LocationConstraint']) + '.amazonaws.com'

    def find_aws_acct(self) -> str:
        """
        Returns the logged in users ID.
        This will only be useful once we can tag sources and not just assets. For now this is unused.

        :return: the account string
        """
        from sh import aws
        cmd = aws('sts', 'get-caller-identity', '--output', 'json')
        acc: Dict[str, str] = json.loads(str(cmd))
        return 'AWS_ACCT_ID:' + str(acc['Account'])


class GoogleCloudProvider(CloudProvider):
    def __init__(self):
        self.name = "Google Cloud"

    def get_ip_ranges(self) -> Dict[str, int]:
        prefixes = {}
        url = 'https://www.gstatic.com/ipranges/cloud.json'
        response = requests.get(url).text
        data = json.loads(response)
        for ips in data['prefixes']:
            if ips.__contains__('ip4Prefix'):
                prefixes[ips['ip4Prefix']] = 1
            if ips.__contains__('ip6Prefix'):
                prefixes[ips['ip6Prefix']] = 1
        return prefixes

    def get_instance_ips(self) -> Dict[str, int]:
        from sh import gcloud
        ips = {}
        ipscmd = gcloud('compute', 'instances', 'list')
        thislist = [y for y in (x.strip() for x in ipscmd.splitlines()) if y]

        skipfirst = 0
        for addresses in thislist:
            if skipfirst == 0:
                skipfirst = 1
                continue
            ips[addresses[68:83].rstrip()] = 1

        return ips


class AzureProvider(CloudProvider):
    def __init__(self):
        self.name = "Azure"

    def get_ip_ranges(self) -> Dict[str, int]:
        prefixes = {}
        payload = '{ "region":  "all", "request":  "dcip" }'
        url = 'https://azuredcip.azurewebsites.net/api/azuredcipranges'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        r = requests.post(url, data=payload, headers=headers)
        thejson = r.json()
        for i in thejson:
            for ip in thejson[i]:
                prefixes[ip] = 1
        return prefixes

    def get_instance_ips(self) -> Dict[str, int]:
        from sh import az
        ips = {}
        ipscmd = az('vm', 'list-ip-addresses', '--output', 'yaml')

        thislist = [y for y in (x.strip() for x in ipscmd.splitlines()) if y]
        for i in thislist:
            if 'ipAddress' in i:
                arra = i.split()
                ips[arra[1].rstrip()] = 1

        return ips


def get_provider(provider: str) -> CloudProvider:
    """
    Returns the provider based on the argument string.

    :param provider: the provider name, either 'amazon-ec2', 'google-cloud' or 'azure'
    :return: a new CloudProvider object
    """
    if provider == 'amazon-ec2':
        return AWSProvider()
    elif provider == 'google-cloud':
        return GoogleCloudProvider()
    elif provider == 'azure':
        return AzureProvider()
