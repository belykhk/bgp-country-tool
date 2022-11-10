#!/usr/bin/env python3

"""
Author - Kostya Belykh k@belykh.su
Language - Python 3.8+
This script is designed to parse data from country network addresses and 
generate configuration file for bind to distribute as BGP table
"""

from optparse import OptionParser
from netaddr import IPNetwork, cidr_merge
import logging
import time
import os
import json
import sys
import urllib.request
import ipaddress
import math

start       = time.time()
logger      = logging.getLogger()

def parseCommandOptions():

    # Parsing input parameters
    p = OptionParser(add_help_option=False,
                     usage = '%prog [options]'
    )
    p.add_option('-h', '--help',
                 action = 'store_true',
                 dest = 'help',
                 help = 'Show this message and exit'
    )
    p.add_option('-l', '--logging',
                 dest = 'enablelogging',
                 help = 'Enable logging to STDOUT',
                 action='store_true'
    )

    (options, args) = p.parse_args()

    if options.help:
        p.print_help()
        exit()

    ## Setup logging
    if options.enablelogging:
        loglevel = 'INFO'
        logFormatStr = '%(asctime)s - %(levelname)-8s - %(message)s'
        logger.setLevel(loglevel)
        chandler = logging.StreamHandler()
        formatter = logging.Formatter(logFormatStr)
        chandler.setFormatter(formatter)
        logger.addHandler(chandler)

    main()

def main():
    logging.info('************************************************************')
    logging.info('Script started')

    logging.info('Importing configuration file')
    try: 
        with open(os.path.join(sys.path[0],'config.json'), 
                  encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        sys.exit('Configuration file not found, exiting')

    logging.info('Current configuration:')
    logging.info('  Sources: {}'.format(config['Sources']))
    logging.info('  Enable IPv4: {}'.format(bool(config['EnableIPv4'])))
    logging.info('  Enable IPv6: {}'.format(bool(config['EnableIPv6'])))
    logging.info('  Output file: {}'.format(config['OutputFile']))

    report = list()

    for s in config['Sources']:
        logging.info('Retreiwing data from {}'.format(s['Name']))
        with urllib.request.urlopen(s['Address']) as f:
            for line in f.read().decode('utf-8').splitlines():
                l = line.split('|')
                try:
                    if l[1] in config['Countries']:
                        if l[2] == 'ipv4' and bool(config['EnableIPv4']) == True:
                            network = str(
                                ipaddress.ip_network(
                                    str(
                                        '{}/{}'.format(
                                            l[3],
                                            str(
                                                int(32-math.log(int(l[4]),2))
                                            )
                                        )
                                    ), strict=False
                                )
                            )
                            if network not in report:
                                report.append(network)
                        if l[2] == 'ipv6' and bool(config['EnableIPv6']) == True:
                            network = str(
                                ipaddress.ip_network(
                                    str(
                                        '{}/{}'.format(
                                            l[3],
                                            l[4]
                                        )
                                    ), strict=False
                                )
                            )
                            if IPNetwork(addr=network) not in report:
                                report.append(IPNetwork(addr=network))
                except IndexError:
                    # Sometimes lines do not have separators 
                    pass
    logging.info('Report generation complete')

    logging.info('Summarizing networks')
    output = cidr_merge(report)

    logging.info('Saving report to {}'.format(config['OutputFile']))
    with open(config['OutputFile'], 'w') as file:
        for line in output:
            file.write('route {} reject;\n'.format(str(line)))
        file.close

    logging.info('Script finished. Runtime: {} seconds.'.format(
        str(round(time.time() - start, 3))
        )
    )

if __name__ == '__main__':
    parseCommandOptions()