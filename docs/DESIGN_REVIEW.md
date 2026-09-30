# Design review — Gmail Cleaner UI

Reviewed 28 September 2026 against `templates/index.html` and `static/js`. The goal was functional clarity: can someone tell what the product does, and can they reach the actions the backend already supports?

## What was getting in the way

The shell introduced itself as "Unsubscribe". The page title, logo, and first sidebar item all used that word, while Delete, Mark as Read, and Search & Export are equal jobs. A returning user could not tell this was Gmail Cleaner.

Search chips included a leftover query, "From beta", which does not describe a Gmail operator and looks like a private shortcut.

The Unsubscribe view documented a label workflow in the README, and `export.js` already called `POST /api/process-unsubscribe-label`, but the page had no button. The script would also throw if that button was missing, because it wrote to the button before checking it existed.

Delete offered Label, Archive, Important, Download, and Delete as disabled buttons with no explanation. The enable path lives in `delete.js` and only turns them on after a sender scan returns rows.

Preview was advertised on each sender row and implemented in `static/js/preview.js` and `app/services/gmail/preview.py`. The page never loaded `preview.js` or `preview.css`, and no route exposed the service. Clicking Preview threw in the browser.

Label Manager is a separate product. It was not linked from this UI, and its launcher was pinned to one absolute path and one token file. That is covered in [LABEL_MANAGER.md](LABEL_MANAGER.md), not by adding a second app inside this page.

## Changes made with this review

- Header and document title now say Gmail Cleaner. The sidebar still names each job.
- Search chips start with Unread and Promotions instead of the leftover query.
- Unsubscribe view has a "Process the Unsubscribe label" action wired to the existing endpoint.
- Delete toolbar explains that actions stay off until a scan finishes, then tells you to select senders.
- Preview modal is loaded, styled, and backed by `POST /api/preview-emails`.
- The menu button has an accessible name.

## Follow-up changes

1. **Select-to-act on Delete.** Toolbar actions stay disabled until at least one sender is checked. The Delete button shows the selected count.
2. **Search vs filter bar.** Search says the filter bar belongs to Scan, Delete, and Mark as Read. "Copy scan filters into this search" writes those values into the search form.
3. **Account-scoped results.** Saved scans are stored per email address. Switching accounts reloads that mailbox's own cache instead of the previous one. Signing out clears the active mailbox's cache.
4. **Label Manager link.** The Delete empty state links to Label Manager on port 8504.
5. **Sidebar.** Support is a footer link. The first control in the sidebar is Unsubscribe.
6. **Work account.** The corporate sign-in option stays hidden unless `credentials_unidays.json` is present.

## Label Manager UI

The Streamlit screen already does the job: tree, search, create, rename, move, and a two-step delete. The functional gaps were outside the widgets: launch only worked from one machine path, and auth was tied to a single token filename. Both now go through `Label Manager.bat` and `label_manager_auth.py`.

A later UI pass can drop the emoji markers in the tree and use the same type scale as Gmail Cleaner, so the two products feel related. That is visual, not a blocked workflow.
