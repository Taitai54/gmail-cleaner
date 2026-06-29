#!/usr/bin/env python3
"""Gmail label manager: list, rename, move, delete."""

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
]
CREDS_DIR = Path(__file__).parent
CREDS_FILE = CREDS_DIR / 'credentials_gmail.json'
TOKEN_FILE = CREDS_DIR / 'token_msego54_gmail.com.json'


def get_service():
    import json as _json
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        else:
            # credentials_gmail.json is a 'web' type client — must inject
            # redirect_uri explicitly and use from_client_config
            raw = _json.loads(CREDS_FILE.read_text(encoding='utf-8-sig'))
            section = dict(raw.get('web') or raw.get('installed') or {})
            wrapper_key = 'web' if 'web' in raw else 'installed'
            redirect_uri = 'http://127.0.0.1:8767/'
            uris = list(section.get('redirect_uris') or [])
            if redirect_uri not in uris:
                uris.append(redirect_uri)
            section['redirect_uris'] = uris
            flow = InstalledAppFlow.from_client_config({wrapper_key: section}, SCOPES)
            flow.redirect_uri = redirect_uri
            creds = flow.run_local_server(port=8767)
            TOKEN_FILE.write_text(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def get_user_labels(service):
    result = service.users().labels().list(userId='me').execute()
    return [l for l in result.get('labels', []) if l['type'] == 'user']


def cmd_list(service, args):
    labels = sorted(get_user_labels(service), key=lambda l: l['name'].lower())
    printed = set()
    for label in labels:
        parts = label['name'].split('/')
        for i, part in enumerate(parts):
            path = '/'.join(parts[: i + 1])
            if path not in printed:
                indent = '  ' * i
                prefix = '└─ ' if i > 0 else ''
                print(f"{indent}{prefix}{part}")
                printed.add(path)


def cmd_rename(service, args):
    labels = get_user_labels(service)
    target = next((l for l in labels if l['name'] == args.old_name), None)
    if not target:
        print(f"Label not found: {args.old_name!r}", file=sys.stderr)
        sys.exit(1)

    service.users().labels().update(
        userId='me', id=target['id'], body={**target, 'name': args.new_name}
    ).execute()
    print(f"Renamed: {args.old_name!r} → {args.new_name!r}")

    children = [l for l in labels if l['name'].startswith(args.old_name + '/')]
    for child in children:
        new_child_name = args.new_name + child['name'][len(args.old_name):]
        service.users().labels().update(
            userId='me', id=child['id'], body={**child, 'name': new_child_name}
        ).execute()
        print(f"  Cascaded: {child['name']!r} → {new_child_name!r}")


def cmd_move(service, args):
    leaf = args.label_name.split('/')[-1]
    new_name = f"{args.new_parent}/{leaf}" if args.new_parent else leaf
    args.old_name = args.label_name
    args.new_name = new_name
    cmd_rename(service, args)


def cmd_delete(service, args):
    labels = get_user_labels(service)
    target = next((l for l in labels if l['name'] == args.label_name), None)
    if not target:
        print(f"Label not found: {args.label_name!r}", file=sys.stderr)
        sys.exit(1)

    children = [l for l in labels if l['name'].startswith(args.label_name + '/')]
    if children and not args.cascade:
        print(f"Label has {len(children)} child label(s). Use --cascade to delete them too.")
        for c in children:
            print(f"  {c['name']}")
        sys.exit(1)

    suffix = f" and {len(children)} child label(s)" if children else ""
    confirm = input(f"Delete {args.label_name!r}{suffix}? [y/N] ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    for child in children:
        service.users().labels().delete(userId='me', id=child['id']).execute()
        print(f"Deleted child: {child['name']!r}")

    service.users().labels().delete(userId='me', id=target['id']).execute()
    print(f"Deleted: {args.label_name!r}")


def main():
    parser = argparse.ArgumentParser(description='Gmail label manager')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('list', help='Show label tree')

    r = sub.add_parser('rename', help='Rename a label (cascades to children)')
    r.add_argument('old_name', help='Current full label name e.g. "Work/Projects"')
    r.add_argument('new_name', help='New full label name e.g. "Work/ActiveProjects"')

    m = sub.add_parser('move', help='Move label under a new parent')
    m.add_argument('label_name', help='Label to move e.g. "Work/Projects"')
    m.add_argument('new_parent', nargs='?', default='',
                   help='New parent label (omit to move to root)')

    d = sub.add_parser('delete', help='Delete a label (messages keep other labels)')
    d.add_argument('label_name', help='Full label name to delete')
    d.add_argument('--cascade', action='store_true', help='Also delete child labels')

    args = parser.parse_args()
    service = get_service()
    {'list': cmd_list, 'rename': cmd_rename, 'move': cmd_move, 'delete': cmd_delete}[
        args.command
    ](service, args)


if __name__ == '__main__':
    main()
