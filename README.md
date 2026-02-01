# Metanet DNS Script

The Python script `metanet.py` allows customers of [metanet.ch](https://metanet.ch) to edit DNS records.

Among accounting tasks, Metanet's customer portal [my.metanet.ch](https://my.metanet.ch) allows to edit DNS records of the booked domains.
However, there is no API to automate editing DNS records. The script `metanet.py` scraps the screen, i.e., browses the portal
and thereby enables to control the DNS editor, i.e., allows to view, add, and remove DNS records (automation).

```text
usage: Metanet DNS Script [-h] [-t [{NS,MX,TXT,ACME}]] uid pwd domkey [{view,add,remove}] [value]

View, add, or remove DNS records

positional arguments:
  uid                   User identification (number)
  pwd                   Password
  domkey                DOMAIN.TLD, *.DOMAIN.TLD, or SUB.DOMAIN.TLD used as key
  {view,add,remove}     Operation applied
  value                 Value to be matched or added

options:
  -h, --help            show this help message and exit
  -t, --type [{NS,MX,TXT,ACME}]
                        Kind of DNS record
```

The script does not need to be configured. It takes the user ID and the corresponding password as positional arguments.
For convenience, one can wrap `metanet.py` via Shell script:

```bash
#!/usr/bin/env bash
#
HERE=$(cd "$(dirname "$0")" && pwd -P)

"${HERE}/metanet.py" 12345 "mypassword" "$@"
```

This way, one can rely on `metanet.sh` and can omit the user ID and the password and only supply subsequent arguments.
It is recommended to quote the password to avoid intepretation by the Shell, e.g., `*` is interpreted.

Given the wrapper, the domain or domain-key is the required first argument to be supplied.
The domain-key is used to edit the DNS records of the respective domain and to select the actual record.
It is recommended to quote the domain-key to avoid intepretation by the Shell,
e.g., `*.domain.com` is otherwise interpreted.

In case of adding or removing a record, a value can be supplied as well to further narrow the matching record.
Beyond positional arguments, the script allows to specify the type or kind of DNS-record (TXT, NS, MX, etc).
The default type is a TXT-record.

## View DNS records

The **view** command is the default operation if not specified otherwise.
Since DNS-records are public, there is no actual need for the script.
However, the **view** command exists for convenience and confirms accessing the Metanet account.

```bash
metanet.sh py domain.com
```

Above command lists all TXT-records of "domain.com". The given domain must be booked with the authenticated Metanet account.

## Add DNS records

The **add** command can be specified to add a DNS-record.

```bash
metanet.sh py domain.com add myvalue
```

## Remove DNS records

The **remove** command can be specified to delete a DNS-record.

```bash
metanet.sh py domain.com remove myvalue
```

If a value is not given, all records for the given key will be deleted!

## Edit DNS records

Modifying a DNS-record can be achieved by deleting and recreating a record, i.e., **remove** followed by **add**.
