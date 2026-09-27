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
# pylint: disable=bare-except,invalid-name
#
"""
Metanet DNS Script: view, add, or remove DNS records.
"""
import argparse
import os
import stat
import sys

from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import mechanize


def credentials_from_file():
    """Read METANET_UID and METANET_PWD (KEY=VALUE lines) from a config file."""
    result = {}
    paths = [os.environ.get("METANET_CONF", ""), "/etc/metanet.conf"]
    paths.append(os.path.expanduser("~/.metanet.conf"))
    for path in [p for p in paths if p and os.path.isfile(p)]:
        if os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            print(f"WARNING: {path} is accessible by group or others (chmod 600)!")
        with open(path, encoding="utf-8") as conf:
            for line in conf:
                key, sep, value = line.strip().partition("=")
                if sep and key.strip() in ("METANET_UID", "METANET_PWD"):
                    result[key.strip()] = value.strip().strip("'\"")
        break
    return result


def open_dns_editor(browser, domain_url):
    """Open the DNS editor of the domain, discard pending edits, return its table."""
    browser.open(domain_url)
    browser.follow_link(text="DNS-Verwaltung")
    try:  # the discard link only exists if edits are pending
        browser.follow_link(text="Änderungen verwerfen")
    except:  # noqa: E722
        pass
    page = BeautifulSoup(browser.response().read(), "html.parser")
    return page.find("table", class_="table-dns-editor")


def records(editor, kind, name):
    """(name, value, row) of all records of kind; all names if name is empty."""
    result = []
    for row in editor.find_all("tr"):
        head, cols = row.find("th"), row.find_all("td")
        if head is None or len(cols) < 3 or kind != cols[1].text.strip():
            continue
        key = head.text.strip()
        if not name or key == name:
            result.append((key, cols[2].text.strip(' "'), cols))
    return result


if __name__ == "__main__":
    # legacy form "metanet.py UID PWD ..." (UID is a number) stays supported
    argv = sys.argv[1:]
    if 2 <= len(argv) and argv[0].isdigit():
        argv = ["--uid", argv[0], "--pwd", argv[1]] + argv[2:]
    config = credentials_from_file()

    argparser = argparse.ArgumentParser(
        prog="Metanet DNS Script", description="View, add, or remove DNS records"
    )
    argparser.add_argument(
        "--uid",
        default=os.environ.get("METANET_UID", config.get("METANET_UID")),
        help="User identification (number), else METANET_UID or config file",
    )
    argparser.add_argument(
        "--pwd",
        default=os.environ.get("METANET_PWD", config.get("METANET_PWD")),
        help="Password, else METANET_PWD or config file",
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
    args = argparser.parse_args(argv)
    if not args.uid or not args.pwd:
        print("ERROR: credentials missing (arguments, METANET_UID/PWD, or config)!")
        sys.exit(1)
    if "add" == args.command and not args.value:
        print("ERROR: no value specified!")
        sys.exit(1)

    DOMLST = args.domkey.split(".")
    DOMAIN, SUBLEN = ".".join(DOMLST[-2:]), len(DOMLST) - 2
    SUBDOM = ".".join(DOMLST[0:SUBLEN]) if 0 < SUBLEN else ""

    KIND = args.type
    if "ACME" == KIND:
        KIND = "TXT"  # ACME is a pseudo-type
        # challenge lives at _acme-challenge.[SUB.]DOMAIN (a wildcard maps to DOMAIN)
        if not SUBDOM.startswith("_acme-challenge"):
            SUBDOM = "_acme-challenge" + (
                f".{SUBDOM}" if SUBDOM and "*" != SUBDOM else ""
            )
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
    NAME = f"{SUBDOM}.{DOMAIN}" if SUBDOM else DOMAIN

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
    try:  # the Domains link only exists after a successful login
        br.follow_link(text="Domains")
    except:  # noqa: E722
        print("ERROR: login failed!")
        sys.exit(1)
    try:
        br.follow_link(text=DOMAIN)
    except:  # noqa: E722
        print(f"ERROR: domain {DOMAIN} not found in this account!")
        sys.exit(1)
    DOMURL = br.geturl()  # pylint: disable=assignment-from-none

    print(  # show request being performed
        f"{args.command.upper()} {KIND}: {NAME}"
        + (f" {args.value}..." if args.value else "...")
    )
    table = open_dns_editor(br, DOMURL)
    # view without a subdomain lists every record of the kind
    MATCH = records(table, KIND, "" if "view" == args.command and not SUBDOM else NAME)
    HIT = False

    if "view" == args.command:
        for curkey, curval, _ in MATCH:
            if not args.value or curval == args.value:
                print(f'{args.command.upper()} {KIND}: {curkey} = "{curval}"')
                HIT = True
    elif "add" == args.command:
        if any(curval == args.value for _, curval, _ in MATCH):
            print(f'Value "{args.value}" already added.')
            HIT = True
        else:  # no existing record of that name is needed
            try:
                br.select_form(nr=0)  # select record type
                br["type"] = [KIND]
                br.submit()
                br.select_form(nr=0)  # (sub-)domain and value
                if SUBDOM:
                    br["subDomain"] = SUBDOM
                br["textValue"] = args.value
                br.submit()
                br.follow_link(text="Jetzt speichern")
                HIT = True
            except:  # noqa: E722
                print(f"ERROR: failed to add {KIND}-record!")
                sys.exit(1)
    elif "remove" == args.command:
        # without a value, every record of that name is removed (one per round,
        # the editor page changes after each save)
        for _ in range(len(MATCH)):
            victim = next(
                (
                    cols
                    for _, curval, cols in MATCH
                    if not args.value or curval == args.value
                ),
                None,
            )
            if victim is None:
                break
            try:
                br.open(victim[3].find("a", class_="delete")["href"])
                br.follow_link(text="Jetzt speichern")
                HIT = True
            except:  # noqa: E722
                print(f"ERROR: failed to remove {KIND}-record!")
                sys.exit(1)
            MATCH = records(open_dns_editor(br, DOMURL), KIND, NAME)
    else:  # should not happen
        print("ERROR: unknown command!")
        sys.exit(1)
    # warn if request did match any record
    if not HIT:
        print("No action performed!")
