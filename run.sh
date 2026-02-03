#!/usr/bin/env bash


# set token
#cat > "$HOME/.pypirc" << EOF
#...
#EOF

# build
rm -rf dist src/*.egg-info
python3 -m pip install --upgrade build
python3 -m build

# upload
python3 -m pip install --upgrade twine
#python3 -m twine upload --repository testpypi dist/* --verbose
python3 -m twine upload --repository pypi dist/* --verbose

# Usage
# pip install -U -i https://test.pypi.org/simple/ pylib-test
# pip install -U pylib-test
# pip install -U pylib-aridge
