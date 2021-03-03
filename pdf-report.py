import os
from argparse import ArgumentParser
from PyPDF2 import PdfFileMerger
from datetime import datetime
from bitdiscovery.api import BitDiscoveryApi, try_multiple_times
from bitdiscovery.pdf import PdfBuilder, PdfPage
from typing import List, Dict, Any, Optional
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

pages: List[PdfPage] = [
    PdfPage('ports.ports', 'Listening Ports', "The most common listening ports on the Internet-accessible assets."),
    PdfPage('own_header.responsecode', 'HTTP/S Response Codes',
            'The HTTP/S response codes for websites which represent whether the site is OK (200-299 responses), the page is redirecting (300-399 responses), content is not found (400 responses), or an error is found (500 responses)'),
    PdfPage('wtech.Content Management Systems', 'Content Management Systems',
            "A content management system (CMS) is a software application that can be used to manage the creation and modification of digital content."),
    PdfPage('wtech.Blogs', 'Blogs',
            "A blog is a discussion or informational website published consisting of discrete, often informal diary-style text entries (posts)."),
    PdfPage('ipgeo.asn', 'ASNs',
            "The top Autonomous System Numbers (ASNs) where the Internet-accessible assets are located by IP-address range. ASNs are a unique number that's available globally to identify an autonomous system and which enables that system to exchange exterior routing information with other neighboring autonomous systems."),
    PdfPage('ssl.issuer_CN', 'SSL/TLS Certificate Authorities',
            "The top SSL/TLS Certificate Authorities (CAs) seen in use by the Internet-accessible assets. A CA is an entity that issues digital certificates."),
    PdfPage('ssl.sslerror', 'SSL/TLS Errors',
            'The SSL/TLS errors that are found on the website in question as seen by an Internet browser like Chrome.'),
    PdfPage('rbls.rbls', 'Reputation Block Lists',
            'Reputation Block Lists protect home and corporate users from visiting sites on the Internet that may have malware, or may be sending spam emails or advertising to users.'),
    PdfPage('ipgeo.country', 'Hosting Countries',
            "The top countries where the Internet-accessible assets are physically located as determined by third-party geolocation of IP-address ranges."),
    PdfPage('wtech.Content Delivery Networks', 'Hosted by CDNs',
            "The top Content Delivery Networks (Akamai, Cloudflare, Fastly, and others) where the Internetaccessible assets are being delivered, which is determined by their well-known and published IPaddress ranges. CDNs refers to a geographically distributed group of servers which work together to provide fast delivery of Internet content."),
    PdfPage('own_header.server', 'Servers',
            "The top web servers running on the Internet-accessible assets based upon their HTTP response headers. The following data may include software distribution, major version, and minor version."),
]

parser = ArgumentParser(description="Output PDF report about your Bit Discovery inventory.")
parser.add_argument('apikey', metavar="APIKEY", type=str, help="Your Bit Discovery API key.")
parser.add_argument('--env', choices=['dev', 'staging', 'prod'], default="dev",
                    help="The Bit Discovery environment (by default 'dev')")
parser.add_argument('--offset', type=int, default=0, help="Offset to the API request data (by default 0).")
parser.add_argument('--limit', type=int, default=500, help="Limit to the API request data (by default 500).")
parser.add_argument('--multiple', action='store_true', help="A flag to pull all of your inventories at once.")
args = parser.parse_args()

APIKEY: str = args.apikey
APIURL: str = "https://bitdiscovery.com/api/1.0"
# TODO, fix this to go above 500
OFFSET: int = args.offset
LIMIT: int = args.limit
MULTIPLE: bool = args.multiple
PDF_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf")

print("Initializing and pulling assets from Bit Discovery...")

# Retrieve inventory or list of inventories from Bit Discovery API
api = BitDiscoveryApi(APIURL, APIKEY)
inventories_json: Dict[str, Any] = {}
try:
    inventories_json = api.find_inventories(OFFSET, LIMIT)
except:
    print("API call failed. Try again later.")
    exit(1)

# If multiple flag is on, use list of inventories
inventories: Dict[str, str] = {}
if MULTIPLE:
    for inventory in inventories_json['list']:
        inventories[inventory['inventory_name']] = inventory['api_key']
else:
    inventories[inventories_json['actualInventory']['inventory_name']] = APIKEY

for entityname in inventories:
    print(f"Starting inventory: {str(entityname)}.")

    inventory_name = entityname.replace(" ", "_")
    report_date = datetime.now().strftime("%Y%m%d")
    title_report_filename = f'{inventory_name}-{report_date}-1.pdf'
    body_report_filename = f'{inventory_name}-{report_date}-2.pdf'
    report_filename = f'{inventory_name}-{report_date}.pdf'

    # Build title page
    pdf = PdfBuilder(entityname, PDF_DIR)
    pdf.add_title_page()
    pdf.save(title_report_filename)

    # Build body of the document
    pdf = PdfBuilder(entityname, PDF_DIR)

    # Query Bit Discovery API for more information
    inventory_apikey = inventories[entityname]
    api = BitDiscoveryApi(APIURL, inventory_apikey)
    querytypes = "%2C".join(map(lambda page: page.key, pages))
    result: Optional[Dict[str, Any]] = try_multiple_times(
        lambda: api.get_dashboard(querytypes),
        max_tries=5
    )

    if result is None:
        print("\tAPI call failed too many times. Try again later.")
        exit(1)

    totalsize: int = result['stats']['total']
    domaincount: int = result['stats']['domaincount']
    subdomaincount: int = result['stats']['subdomaincount']

    pagedata: Dict[str, List[Dict[str, Any]]] = {}
    for aggregation in result['aggregations']:
        pagedata[aggregation['column']] = aggregation['data']

    # Add asset page
    pdf.add_count_page(
        "asset",
        """
        "A domain name, subdomain, or IP address and/or combination thereof of a device connected to the Internet or
        internal network. An asset may include but is not limited to web servers, name servers, IoT devices, network
        printers, etc. Example: foo.tld, bar.foo.tld, x.x.x.x"
        """,
        totalsize
    )

    # Add domain page
    pdf.add_count_page(
        "domain",
        """
        A domain name is a label that identifies a network domain. Domain names are used to identify Internet resources,
        such as computers, networks and services, with an easy-to-remember text label that is easier to memorize than the
        numerical addresses used in Internet protocols.
        """,
        domaincount
    )

    # Add subdomain page
    pdf.add_count_page(
        "subdomain",
        """
        A subdomain is a domain name with a hostname appended, which is sometimes more accurately described as a fully
        qualified domain name (FQDN).
        """,
        subdomaincount
    )

    # Build graph pages for each page type
    for (i, page) in enumerate(pages):
        print("\tBuilding page for: " + str(page.key))
        data = pagedata[page.key] if page.key in pagedata else []

        # Generate graph
        bardata: List[int] = [row["value"] for row in data if str(row['name']) != "__missing__"]
        fig = plt.figure(figsize=(9, 5))
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['bottom'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.gca().spines['left'].set_visible(False)
        plt.ylabel('Assets')
        plt.grid()
        my_colors = ['#3C84C1', '#5DC3C7', '#53b006', '#EEAE68', '#DD6069']
        plt.bar(list(range(len(bardata))), bardata, color=my_colors)
        plt.xticks([])
        plt.show()
        imagename = f'tmp{i}.png'
        plt.savefig(os.path.join(PDF_DIR, imagename), transparent=True)

        # Generate page from page data and graph
        pdf.add_graph_page(page, data, imagename, totalsize)

    pdf.save(body_report_filename)

    # Merge the parts of PDFs
    print("\tCombining PDFs into one.")
    merger = PdfFileMerger()
    merger.append(os.path.join(PDF_DIR, title_report_filename))
    merger.append(os.path.join(PDF_DIR, '2-6.pdf'))
    merger.append(os.path.join(PDF_DIR, body_report_filename))
    merger.append(os.path.join(PDF_DIR, '15-17.pdf'))

    output = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), report_filename), 'wb')
    merger.write(output)
    output.close()

    # Remove temporary files
    print("\tCleaning up.")
    image_files = [f'tmp{i}.png' for i in range(0, len(pages))]
    for filename in image_files + [title_report_filename, body_report_filename]:
        try:
            os.remove(os.path.join(PDF_DIR, filename))
        except:
            print("\tCouldn't remove: {}".format(os.path.join(PDF_DIR, filename)))

    print("\t\tYour report is located at: {}".format(os.path.join(os.path.dirname(os.path.abspath(__file__)), report_filename)))

print("\nComplete.")
