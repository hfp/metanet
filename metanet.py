#!/usr/bin/env python3
###############################################################################
# Copyright (c) Hans Pabst - All rights reserved.                             #
# This file is part of the Metanet DNS Script.                                #
#                                                                             #
# For information on the license, see the LICENSE file.                       #
# Further information: https://github.com/hfp/metanet/                        #
# SPDX-License-Identifier: BSD-3-Clause                                       #
###############################################################################
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import mechanize
import argparse

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

    domlst = args.domkey.split(".")
    domain, sublen = ".".join(domlst[-2:]), len(domlst) - 2
    subdom = ".".join(domlst[0:sublen]) if 0 < sublen else ""

    key = args.domkey
    type = args.type
    if "ACME" == type:
        type = "TXT"  # ACME is a pseudo-type
        if not subdom and "view" != args.command:
            subdom = "_acme-challenge"
    if "MX" == type:
        if "*" == subdom:
            print('ERROR: subdomain cannot be "*"!')
            exit(1)
    elif "NS" == type:
        if subdom:
            print("ERROR: subdomain cannot be specified!")
            exit(1)
    elif "TXT" != type:  # should not happen
        print("ERROR: unknown record type!")
        exit(1)

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
    br.follow_link(text=domain)

    dns = br.follow_link(text="DNS-Verwaltung")
    content = BeautifulSoup(dns.read(), "html.parser")
    table = content.find("table", class_="table-dns-editor")
    try:
        br.follow_link(text="Änderungen verwerfen")
    except:  # noqa: E722
        pass

    hit, error = False, ""
    print(  # show request being performed
        f"{args.command.upper()} {type}: {key}"
        + (f" {args.value}..." if args.value else "...")
    )
    for row in table.find_all("tr"):
        curkey = row.find("th").text.strip()
        if key == curkey or (not subdom and "view" == args.command):
            cols = row.find_all("td")
            if type == cols[1].text.strip():
                curval = cols[2].text.strip(' "')
                if "view" == args.command:
                    if not args.value or curval == args.value:
                        print(f'{args.command.upper()} {type}: {curkey} = "{curval}"')
                        hit = True
                elif "add" == args.command:
                    if args.value and curval != args.value:
                        try:
                            # select record type
                            br.select_form(nr=0)
                            br["type"] = [type]
                            br.submit()
                            # (sub-)domain and value
                            br.select_form(nr=0)
                            if subdom:
                                br["subDomain"] = subdom
                            br["textValue"] = args.value
                            br.submit()
                            br.follow_link(text="Jetzt speichern")
                            hit = True
                        except:  # noqa: E722
                            error = f"ERROR: failed to add {type}-record!"
                            continue
                        break
                    elif args.value:
                        print(f'Value "{curval}" already added.')
                        break
                    elif error:
                        print(error)
                        break
                    else:
                        print("ERROR: no value specified!")
                        exit(1)
                elif "remove" == args.command:
                    if not args.value or curval == args.value:
                        try:
                            remove = cols[3].find("a", class_="delete")
                            br.open(remove["href"])
                            br.follow_link(text="Jetzt speichern")
                            hit = True
                        except:  # noqa: E722
                            print(f"ERROR: failed to remove {type}-record!")
                        break
                else:  # should not happen
                    print("ERROR: unknown command!")
                    exit(1)
    # warn if request did match any record
    if not hit:
        print("No action performed!")
