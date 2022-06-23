set -e
pycodestyle folderparser
pylint -s n folderparser
git diff --check --cached folderparser
cd folderparser && python3 folderparser.py
