"""Wrap docs/plan.html (artifact-style fragment) into docs/index.html for GitHub Pages."""
import io, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
body = io.open(os.path.join(root, "docs", "plan.html"), encoding="utf-8").read()
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<!-- GENERATED from plan.html by tools/build-docs.py; edit plan.html, not this file -->\n'
        '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
io.open(os.path.join(root, "docs", "index.html"), "w", encoding="utf-8", newline="\n").write(page)
print("wrote docs/index.html")
