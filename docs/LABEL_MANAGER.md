# Gmail Label Manager

Label Manager is a second product in this repository. It organizes the Gmail label tree: list, create, rename, move, and delete labels. It does not scan, unsubscribe, or delete mail.

Gmail Cleaner can apply or remove a label on messages from selected senders. That is a cleanup action. Label Manager changes the labels themselves, including nested names such as `Work/Projects`.

## How to launch

**Windows:** double-click `Label Manager.bat` in the project folder.

The script changes to its own folder, checks for `uv` and an OAuth client file, then starts Streamlit:

```bat
uv run --with streamlit python -m streamlit run label_manager_ui.py --server.port 8504 --browser.gatherUsageStats false
```

Open http://127.0.0.1:8504 if the browser does not.

**Command line:**

```bash
uv run --with streamlit python -m streamlit run label_manager_ui.py --server.port 8504 --browser.gatherUsageStats false
```

**CLI (no UI):**

```bash
uv run python label_manager.py list
uv run python label_manager.py rename "Work/Projects" "Work/Active"
uv run python label_manager.py move "Work/Active" "Archive"
uv run python label_manager.py delete "Archive/Old" --cascade
```

Rename and move cascade to child labels. Delete refuses to remove a parent that still has children unless `--cascade` is set. Deleting a label does not delete the messages that carried it.

## Authentication

Both products use Gmail OAuth scopes `gmail.readonly` and `gmail.modify`. Label Manager resolves credentials in this order:

1. `credentials_gmail.json`, then `credentials.json`
2. The active account in `accounts.json`, when that token file exists
3. The only `token_*.json` in the project folder
4. A new desktop OAuth flow on port **8767**, which writes `token_{email}.json` and records the account

If several token files exist and none is marked active, Label Manager stops and asks you to sign in with Gmail Cleaner first.

Do not start a sign-in in both apps at once. They both listen on port 8767 for the Google callback. The apps themselves use different ports: Cleaner on **8766**, Label Manager on **8504**.

## Files

| File | Role |
| --- | --- |
| `label_manager_ui.py` | Streamlit UI: tree, search, create, rename, move, delete |
| `label_manager.py` | Same operations as a command-line tool |
| `label_manager_auth.py` | Shared token and OAuth client resolution |
| `Label Manager.bat` | Windows double-click launcher |

Streamlit is not part of the main Gmail Cleaner install. The launcher pulls it in with `uv run --with streamlit`.

## What the UI does

- Sidebar lists user labels as a tree. Nested labels use `/` in the name, which is how Gmail represents hierarchy.
- Search filters the tree and shows matching branches even when a parent is collapsed.
- Selecting a label opens rename, move, and delete. Rename and move update child names so the tree stays intact.
- Create accepts a full path such as `Work/Projects/Q3`.
- Delete asks for a second confirmation. Children are deleted only when the cascade checkbox is on.
