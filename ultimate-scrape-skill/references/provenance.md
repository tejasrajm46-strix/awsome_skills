# Shared helper provenance

The user-supplied `ultimate-scrape (1).zip` was inspected as a reference. It did
not contain a license file. Before publication, the user chose to publish only
cleared/original material, so imported executable code and the imported HTML
fixture were removed from the distributable tree.

Published `extract_parts.py`, `contact_sheet.py`, `route.py`, tests, fixture and
supporting guidance are original repository implementations. The extraction
interface supports saved HTML, public HTTP HTML, bounded raster downloads, page
data/style tokens and all five format owners. It does not include the original
stealth fetchers, old external-project router, destructive installer or duplicated
Google downloader.

Previous imported versions and the original ZIP remain preserved in ignored
`local-archive/` for the user's private records, not packaged or pushed.

Python's standard library performs parsing and retrieval. Pillow is an optional
installed dependency with its own license; its code is not vendored into this
skill. Original repository code is under the root MIT license.
