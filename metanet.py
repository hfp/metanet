#!/usr/bin/env python3
###############################################################################
# Copyright (c) Hans Pabst - All rights reserved.                             #
# This file is part of the Metanet DNS Script.                                #
#                                                                             #
# For information on the license, see the LICENSE file.                       #
# Further information: https://github.com/hfp/metanet/                        #
# SPDX-License-Identifier: BSD-3-Clause                                       #
###############################################################################
#
# pylint: disable=bare-except
#
"""
Metanet DNS Script: view, add, or remove DNS records.
"""
import argparse
import sys

from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import mechanize

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        prog="Metanet DNS Script", description="View, add, or remove DNS records"
    )
    argparser.add_argument(
        "uid",
        help="User identification (number)",
    )
    argparser.add_argument(
        "pwd",
        help="Password",
    )
    argparser.add_argument(
        "domkey",
        type=str,
        help="DOMAIN.TLD, *.DOMAIN.TLD, or SUB.DOMAIN.TLD used as key",
    )
    argparser.add_argument(
        "command",
        default="view",
        const="view",
        nargs="?",
        choices=["view", "add", "remove"],
        help="Operation applied",
    )
    argparser.add_argument(
        "value",
        nargs="?",
        help="Value to be matched or added",
    )
    argparser.add_argument(
        "-t",
        "--type",
        default="TXT",
        const="TXT",
        nargs="?",
        choices=["NS", "MX", "TXT", "ACME"],
        help="Kind of DNS record",
    )
    args = argparser.parse_args()

    DOMLST = args.domkey.split(".")
    DOMAIN, SUBLEN = ".".join(DOMLST[-2:]), len(DOMLST) - 2
    SUBDOM = ".".join(DOMLST[0:SUBLEN]) if 0 < SUBLEN else ""

    KEY = args.domkey
    KIND = args.type
    if "ACME" == KIND:
        KIND = "TXT"  # ACME is a pseudo-type
        if not SUBDOM and "view" != args.command:
            SUBDOM = "_acme-challenge"
    if "MX" == KIND:
        if "*" == SUBDOM:
            print('ERROR: subdomain cannot be "*"!')
            sys.exit(1)
    elif "NS" == KIND:
        if SUBDOM:
            print("ERROR: subdomain cannot be specified!")
            sys.exit(1)
    elif "TXT" != KIND:  # should not happen
        print("ERROR: unknown record type!")
        sys.exit(1)

    br = mechanize.Browser()
    # br.set_handle_robots(False)
    ua = UserAgent(platforms="desktop")
    br.addheaders = [("User-agent", ua.random)]
    # language matters for subsequent control
    br.open("https://my.metanet.ch/de/")

    br.select_form(class_="form-login")
    br["loginID"] = args.uid
    br["password"] = args.pwd
    br.submit()

    br.follow_link(text="Domains")
    br.follow_link(text=DOMAIN)

    br.follow_link(text="DNS-Verwaltung")
    content = BeautifulSoup(br.response().read(), "html.parser")
    table = content.find("table", class_="table-dns-editor")
    try:
        br.follow_link(text="Änderungen verwerfen")
    except:  # noqa: E722
        pass

    HIT, ERROR = False, ""
    print(  # show request being performed
        f"{args.command.upper()} {KIND}: {KEY}"
        + (f" {args.value}..." if args.value else "...")
    )
    for row in table.find_all("tr"):
        curkey = row.find("th").text.strip()
        if KEY == curkey or (not SUBDOM and "view" == args.command):
            cols = row.find_all("td")
            if KIND == cols[1].text.strip():
                curval = cols[2].text.strip(' "')
                if "view" == args.command:
                    if not args.value or curval == args.value:
                        print(f'{args.command.upper()} {KIND}: {curkey} = "{curval}"')
                        HIT = True
                elif "add" == args.command:
                    if args.value and curval != args.value:
                        try:
                            # select record type
                            br.select_form(nr=0)
                            br["type"] = [KIND]
                            br.submit()
                            # (sub-)domain and value
                            br.select_form(nr=0)
                            if SUBDOM:
                                br["subDomain"] = SUBDOM
                            br["textValue"] = args.value
                            br.submit()
                            br.follow_link(text="Jetzt speichern")
                            HIT = True
                        except:  # noqa: E722
                            ERROR = f"ERROR: failed to add {KIND}-record!"
                            continue
                    elif args.value:
                        print(f'Value "{curval}" already added.')
                    elif ERROR:
                        print(ERROR)
                    else:
                        print("ERROR: no value specified!")
                        sys.exit(1)
                    break
                elif "remove" == args.command:
                    if not args.value or curval == args.value:
                        try:
                            remove = cols[3].find("a", class_="delete")
                            br.open(remove["href"])
                            br.follow_link(text="Jetzt speichern")
                            HIT = True
                        except:  # noqa: E722
                            print(f"ERROR: failed to remove {KIND}-record!")
                        break
                else:  # should not happen
                    print("ERROR: unknown command!")
                    sys.exit(1)
    # warn if request did match any record
    if not HIT:
        print("No action performed!")
