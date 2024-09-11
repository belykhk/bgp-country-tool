#!/usr/bin/env python3

"""
Author - Kostya Belykh k@belykh.su
Language - Python 3.8+
This script is designed to parse data from country network addresses and
generate configuration file for bind to distribute as BGP table. For additional
information please refer to README.md file.
"""

import json
import logging
import math
import os
import sys
import time
import urllib.request
from ipaddress import ip_network
from optparse import OptionParser

from netaddr import cidr_merge

start = time.time()
logger = logging.getLogger()


def netmaskcidr(num_hosts):
    # Return cidr notation of netmask based on number of hosts it contains
    required_bits = math.ceil(math.log2(int(num_hosts)))
    network_bits = 32 - required_bits
    return f"{network_bits}"


def updatesubnet(networks, subnets_to_remove, subnets_to_add):
    networks = cidr_merge(networks)
    returnnetworks = set()
    for network in networks:
        if subnets_to_remove:
            for subnet in subnets_to_remove:
                if ip_network(subnet, strict=False).overlaps(
                    ip_network(network, strict=False)
                ):
                    resultnets = list(
                        ip_network(network, strict=False).address_exclude(
                            ip_network(subnet, strict=False)
                        )
                    )
                    for net in resultnets:
                        returnnetworks.add(str(net))
                else:
                    returnnetworks.add(network)
        else:
            returnnetworks.add(network)
    for subnet in subnets_to_add:
        returnnetworks.add(subnet)
    # Correct data in case some registrars have wrong info about network
    corrected_networks = set()
    for network in returnnetworks:
        n = ip_network(network, strict=False)
        corrected_networks.add(str(f"{n.network_address}/{n.prefixlen}"))
    return corrected_networks


def parseCommandOptions():

    # Parsing input parameters
    p = OptionParser(add_help_option=False, usage="%prog [options]")
    p.add_option(
        "-h",
        "--help",
        action="store_true",
        dest="help",
        help="Show this message and exit",
    )
    p.add_option(
        "-l",
        "--logging",
        dest="enablelogging",
        help="Enable logging to STDOUT",
        action="store_true",
    )
    p.add_option(
        "-c",
        "--config",
        dest="configfile",
        help="Configuration file to use, default is ./config.json",
        default=os.path.join(sys.path[0], "config.json"),
    )

    (options, args) = p.parse_args()

    if options.help:
        p.print_help()
        exit()

    ## Setup logging
    if options.enablelogging:
        loglevel = "INFO"
        logFormatStr = "%(asctime)s - %(levelname)-8s - %(message)s"
        logger.setLevel(loglevel)
        chandler = logging.StreamHandler()
        formatter = logging.Formatter(logFormatStr)
        chandler.setFormatter(formatter)
        logger.addHandler(chandler)

    main(options.configfile)


def main(configfile):
    logging.info("************************************************************")
    logging.info("Script started")

    logging.info("Importing configuration file")
    try:
        with open(configfile, encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        sys.exit("Configuration file not found, exiting")

    logging.info("Current configuration:")

    logging.info("  Sources:")
    for s in config["Sources"]:
        logging.info(f'    Name: {s["Name"]}, Address: {s["Address"]}')
    logging.info(f'  Countries: {config["Countries"]}')

    logging.info(f'  Enable IPv4: {bool(config["EnableIPv4"])}')
    if bool(config["EnableIPv4"]) == True:
        logging.info(f'    IPv4 networks to be appended: {config["AppendIPv4"]}')
        logging.info(f'    IPv4 networks to be excluded: {config["ExcludeIPv4"]}')
        logging.info(f'    Output file for IPv4 networks: {config["OutputFileipv4"]}')

    logging.info(f'  Enable IPv6: {bool(config["EnableIPv6"])}')
    if bool(config["EnableIPv6"]) == True:
        logging.info(f'    IPv6 networks to be appended: {config["AppendIPv6"]}')
        logging.info(f'    IPv6 networks to be excluded: {config["ExcludeIPv6"]}')
        logging.info(f'    Output file for ipv6 networks: {config["OutputFileipv6"]}')

    logging.info(f'  Output format: {config["OutputFormat"]}')

    logging.info("Retrieving data from sources")
    data = {}
    for s in config["Sources"]:
        logging.info(f'  Retreiwing data from {s["Name"]}')
        try:
            with urllib.request.urlopen(s["Address"]) as f:
                data[s["Name"]] = f.read().decode("utf-8").splitlines()
        except urllib.error.URLError as e:
            logging.error(f'  Unable to retrieve data from {s["Name"]}: {e.reason}')
            sys.exit(f'Unable to retrieve data from {s["Name"]}: {e.reason}')

    logging.info("Generating report")
    reportipv4 = set()
    reportipv6 = set()
    for s in config["Sources"]:
        logging.info(f'  Processing data from {s["Name"]}')
        for line in data[s["Name"]]:
            try:
                l = line.split("|")
                if l[1] in config["Countries"]:
                    if l[2] == "ipv4" and bool(config["EnableIPv4"]) == True:
                        reportipv4.add(str(f"{l[3]}/{netmaskcidr(l[4])}"))
                    if l[2] == "ipv6" and bool(config["EnableIPv6"]) == True:
                        reportipv6.add(str(f"{l[3]}/{l[4]}"))
            except IndexError:
                # Sometimes lines do not have separators
                pass
    if bool(config["EnableIPv4"]) == True:
        reportipv4 = updatesubnet(
            reportipv4, config["ExcludeIPv4"], config["AppendIPv4"]
        )
    if bool(config["EnableIPv6"]) == True:
        reportipv6 = updatesubnet(
            reportipv6, config["ExcludeIPv6"], config["AppendIPv6"]
        )

    logging.info("  Report generation complete")
    if bool(config["EnableIPv4"]) == True:
        logging.info(f"    IPv4 networks: {len(reportipv4)}")
    if bool(config["EnableIPv6"]) == True:
        logging.info(f"    IPv6 networks: {len(reportipv6)}")

    logging.info("Saving report")
    if bool(config["EnableIPv4"]) == True:
        logging.info(f'  Saving IPv4 report to {config["OutputFileipv4"]}')
        with open(config["OutputFileipv4"], "w") as file:
            for line in reportipv4:
                file.write(config["OutputFormat"].format(str(line)) + "\n")
            file.close
    if bool(config["EnableIPv6"]) == True:
        logging.info(f'  Saving IPv6 report to {config["OutputFileipv6"]}')
        with open(config["OutputFileipv6"], "w") as file:
            for line in reportipv6:
                file.write(config["OutputFormat"].format(str(line)) + "\n")
            file.close

    logging.info(
        f"Script finished. Runtime: {str(round(time.time() - start, 3))} seconds."
    )


if __name__ == "__main__":
    parseCommandOptions()
