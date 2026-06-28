import os
import sys
import time
import json
import argparse
import urllib.parse
from typing import Dict, Any, List, Optional

import requests
from dotenv import load_dotenv


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


# -----------------------------
# Config / Auth
# -----------------------------

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "y")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def get_access_token() -> str:
    tenant_id = require_env("TENANT_ID")
    client_id = require_env("CLIENT_ID")
    client_secret = require_env("CLIENT_SECRET")

    url = TOKEN_URL_TEMPLATE.format(tenant_id=tenant_id)

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }

    response = requests.post(url, data=data, timeout=60)
    if response.status_code >= 400:
        raise RuntimeError(f"Token request failed: {response.status_code} {response.text}")

    return response.json()["access_token"]


def graph_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def graph_get(token: str, url: str) -> Dict[str, Any]:
    response = requests.get(url, headers=graph_headers(token), timeout=120)
    if response.status_code >= 400:
        raise RuntimeError(f"GET failed: {response.status_code} {url}\n{response.text}")
    return response.json()


def graph_post(token: str, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(url, headers=graph_headers(token), json=payload, timeout=120)
    if response.status_code >= 400:
        raise RuntimeError(f"POST failed: {response.status_code} {url}\n{response.text}")
    if not response.text:
        return {}
    return response.json()


def graph_patch(token: str, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.patch(url, headers=graph_headers(token), json=payload, timeout=120)
    if response.status_code >= 400:
        raise RuntimeError(f"PATCH failed: {response.status_code} {url}\n{response.text}")
    if not response.text:
        return {}
    return response.json()


# -----------------------------
# SharePoint Site / List helpers
# -----------------------------

def resolve_site_id(token: str, hostname: str, site_path: str) -> str:
    site_path = site_path.strip()
    if not site_path.startswith("/"):
        site_path = "/" + site_path

    encoded_path = urllib.parse.quote(site_path)
    url = f"{GRAPH_ROOT}/sites/{hostname}:{encoded_path}"
    site = graph_get(token, url)
    return site["id"]


def get_lists(token: str, site_id: str) -> List[Dict[str, Any]]:
    url = f"{GRAPH_ROOT}/sites/{site_id}/lists?$select=id,displayName,name"
    data = graph_get(token, url)
    return data.get("value", [])


def get_or_create_list(token: str, site_id: str, list_name: str) -> str:
    for sp_list in get_lists(token, site_id):
        if sp_list.get("displayName", "").lower() == list_name.lower():
            return sp_list["id"]

    payload = {
        "displayName": list_name,
        "list": {
            "template": "genericList"
        }
    }

    created = graph_post(token, f"{GRAPH_ROOT}/sites/{site_id}/lists", payload)
    return created["id"]


def get_existing_columns(token: str, site_id: str, list_id: str) -> Dict[str, Dict[str, Any]]:
    url = f"{GRAPH_ROOT}/sites/{site_id}/lists/{list_id}/columns"
    data = graph_get(token, url)
    return {
        c.get("name"): c
        for c in data.get("value", [])
        if c.get("name")
    }


def create_text_column(token: str, site_id: str, list_id: str, name: str, indexed: bool = False) -> None:
    payload = {
        "name": name,
        "text": {},
        "indexed": indexed
    }
    graph_post(token, f"{GRAPH_ROOT}/sites/{site_id}/lists/{list_id}/columns", payload)


def create_number_column(token: str, site_id: str, list_id: str, name: str) -> None:
    payload = {
        "name": name,
        "number": {
            "decimalPlaces": "none"
        }
    }
    graph_post(token, f"{GRAPH_ROOT}/sites/{site_id}/lists/{list_id}/columns", payload)


def create_datetime_column(token: str, site_id: str, list_id: str, name: str) -> None:
    payload = {
        "name": name,
        "dateTime": {
            "displayAs": "default"
        }
    }
    graph_post(token, f"{GRAPH_ROOT}/sites/{site_id}/lists/{list_id}/columns", payload)


def ensure_register_columns(token: str, site_id: str, list_id: str) -> None:
    existing = get_existing_columns(token, site_id, list_id)

    text_columns = [
        ("OneDriveItemId", True),
        ("DriveId", False),
        ("FileName", False),
        ("FilePath", False),
        ("ParentPath", False),
        ("Category", False),
        ("WebUrl", False),
        ("ShareLink", False),
        ("MimeType", False),
        ("CreatedBy", False),
        ("ModifiedBy", False),
        ("ETag", False),
    ]

    number_columns = [
        "SizeBytes",
    ]

    datetime_columns = [
        "CreatedDateTime",
        "LastModifiedDateTime",
        "RegisteredDateTime",
    ]

    for name, indexed in text_columns:
        if name not in existing:
            create_text_column(token, site_id, list_id, name, indexed=indexed)

    for name in number_columns:
        if name not in existing:
            create_number_column(token, site_id, list_id, name)

    for name in datetime_columns:
        if name not in existing:
            create_datetime_column(token, site_id, list_id, name)


# -----------------------------
# OneDrive Enumeration
# -----------------------------

def get_source_drive(token: str, source_user_upn: str) -> Dict[str, Any]:
    encoded_user = urllib.parse.quote(source_user_upn)
    url = f"{GRAPH_ROOT}/users/{encoded_user}/drive"
    return graph_get(token, url)


def get_drive_item_by_path(token: str, drive_id: str, path: str) -> Dict[str, Any]:
    clean_path = path.strip("/")
    if not clean_path:
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root"
    else:
        encoded_path = urllib.parse.quote(clean_path)
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root:/{encoded_path}"

    return graph_get(token, url)


def list_children(token: str, drive_id: str, item_id: str) -> List[Dict[str, Any]]:
    items = []
    url = (
        f"{GRAPH_ROOT}/drives/{drive_id}/items/{item_id}/children"
        "?$select=id,name,webUrl,size,file,folder,parentReference,"
        "createdDateTime,lastModifiedDateTime,createdBy,lastModifiedBy,eTag"
    )

    while url:
        data = graph_get(token, url)
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")

    return items


def walk_drive_folder(token: str, drive_id: str, root_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    found = []

    def walk(item: Dict[str, Any]) -> None:
        if "folder" in item:
            children = list_children(token, drive_id, item["id"])
            for child in children:
                walk(child)
        elif "file" in item:
            found.append(item)

    walk(root_item)
    return found


# -----------------------------
# Link hydration
# -----------------------------

def create_org_view_link(token: str, drive_id: str, item_id: str) -> Optionalurl = f"{GRAPH_ROOT}/drives/{drive_id}/items/{item_id}/createLink"

    payload = {
        "type": "view",
        "scope": "organization",
        "retainInheritedPermissions": True
    }

    result = graph_post(token, url, payload)
    return (
        result.get("link", {}).get("webUrl")
        or result.get("link", {}).get("webHtml")
    )


# -----------------------------
# List item upsert
# -----------------------------

def find_existing_list_item_by_drive_item_id(
    token: str,
    site_id: str,
    list_id: str,
    one_drive_item_id: str
) -> Optionalescaped = one_drive_item_id.replace("'", "''")
    filter_query = urllib.parse.quote(f"fields/OneDriveItemId eq '{escaped}'", safe="()/='$ ")
    url = (
        f"{GRAPH_ROOT}/sites/{site_id}/lists/{list_id}/items"
        f"?$expand=fields&$filter={filter_query}"
    )

    data = graph_get(token, url)
    values = data.get("value", [])
    if not values:
        return None

    return values[0]["id"]


def add_list_item(token: str, site_id: str, list_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "fields": fields
    }
    url = f"{GRAPH_ROOT}/sites/{site_id}/lists/{list_id}/items"
    return graph_post(token, url, payload)


def update_list_item(token: str, site_id: str, list_id: str, item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    payload = fields
    url = f"{GRAPH_ROOT}/sites/{site_id}/lists/{list_id}/items/{item_id}/fields"
    return graph_patch(token, url, payload)


def identity_display_name(identity_set: Optional[Dict[str, Any]]) -> str:
    if not identity_set:
        return ""

    for key in ("user", "application", "device"):
        obj = identity_set.get(key)
        if obj and obj.get("displayName"):
            return obj["displayName"]

    return ""


def build_register_fields(
    item: Dict[str, Any],
    drive_id: str,
    category: str,
    share_link: str
) -> Dict[str, Any]:
    parent_ref = item.get("parentReference", {}) or {}
    parent_path = parent_ref.get("path", "")
    file_obj = item.get("file", {}) or {}

    return {
        "Title": item.get("name", ""),
        "OneDriveItemId": item.get("id", ""),
        "DriveId": drive_id,
        "FileName": item.get("name", ""),
        "FilePath": parent_path + "/" + item.get("name", ""),
        "ParentPath": parent_path,
        "Category": category,
        "WebUrl": item.get("webUrl", ""),
        "ShareLink": share_link or "",
        "MimeType": file_obj.get("mimeType", ""),
        "SizeBytes": item.get("size", 0),
        "CreatedDateTime": item.get("createdDateTime"),
        "LastModifiedDateTime": item.get("lastModifiedDateTime"),
        "RegisteredDateTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "CreatedBy": identity_display_name(item.get("createdBy")),
        "ModifiedBy": identity_display_name(item.get("lastModifiedBy")),
        "ETag": item.get("eTag", ""),
    }


# -----------------------------
# Main
# -----------------------------

def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Enumerate OneDrive for Business files and register links in a SharePoint Microsoft List."
    )
    parser.add_argument("--category", default=os.getenv("DEFAULT_CATEGORY", "Triage"))
    parser.add_argument("--hydrate-links", action="store_true", default=env_bool("HYDRATE_SHARE_LINKS", False))
    parser.add_argument("--no-upsert", action="store_true", default=not env_bool("UPSERT", True))
    args = parser.parse_args()

    source_user_upn = require_env("SOURCE_USER_UPN")
    source_onedrive_path = require_env("SOURCE_ONEDRIVE_PATH")

    target_site_hostname = require_env("TARGET_SITE_HOSTNAME")
    target_site_path = require_env("TARGET_SITE_PATH")
    target_list_name = require_env("TARGET_LIST_NAME")

    upsert = not args.no_upsert

    print("Authenticating to Microsoft Graph...")
    token = get_access_token()

    print("Resolving source OneDrive...")
    drive = get_source_drive(token, source_user_upn)
    drive_id = drive["id"]

    print(f"Source drive: {drive.get('name')} [{drive_id}]")
    print(f"Source path: {source_onedrive_path}")

    root_item = get_drive_item_by_path(token, drive_id, source_onedrive_path)

    print("Enumerating files recursively...")
    files = walk_drive_folder(token, drive_id, root_item)
    print(f"Found files: {len(files)}")

    print("Resolving target SharePoint site...")
    site_id = resolve_site_id(token, target_site_hostname, target_site_path)
    print(f"Target site id: {site_id}")

    print("Getting or creating Microsoft List...")
    list_id = get_or_create_list(token, site_id, target_list_name)
    print(f"Target list: {target_list_name} [{list_id}]")

    print("Ensuring list columns exist...")
    ensure_register_columns(token, site_id, list_id)

    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for idx, item in enumerate(files, start=1):
        file_name = item.get("name", "")
        item_id = item.get("id", "")

        try:
            print(f"[{idx}/{len(files)}] Registering: {file_name}")

            share_link = ""
            if args.hydrate_links:
                share_link = create_org_view_link(token, drive_id, item_id) or ""

            fields = build_register_fields(
                item=item,
                drive_id=drive_id,
                category=args.category,
                share_link=share_link,
            )

            existing_id = None
            if upsert:
                existing_id = find_existing_list_item_by_drive_item_id(
                    token=token,
                    site_id=site_id,
                    list_id=list_id,
                    one_drive_item_id=item_id,
                )

            if existing_id:
                update_list_item(token, site_id, list_id, existing_id, fields)
                updated_count += 1
            else:
                add_list_item(token, site_id, list_id, fields)
                created_count += 1

        except Exception as ex:
            error_count += 1
            print(f"ERROR registering {file_name}: {ex}", file=sys.stderr)

    print("")
    print("Done.")
    print(json.dumps({
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": error_count,
        "source_user": source_user_upn,
        "source_path": source_onedrive_path,
        "target_site": f"{target_site_hostname}{target_site_path}",
        "target_list": target_list_name,
        "category": args.category,
        "hydrated_links": args.hydrate_links,
        "upsert": upsert,
    }, indent=2))

    return 0 if error_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())