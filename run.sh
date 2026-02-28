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
python3 -m twine upload --repository pypi dist/* --verbose  # python3 -m twine upload --repository testpypi dist/* --verbose

# Usage
# pip install -U -i https://test.pypi.org/simple/ pylib-test
# pip install -U pylib-test
# pip install -U pylib-aridge
# download cnt: curl https://pypistats.org/api/packages/pylib-aridge/recent
# download cnt: curl https://pypistats.org/api/packages/pylib-test/recent
# download overall: curl -s https://pypistats.org/api/packages/pylib-aridge/overall | jq -r '.data[] | [.date, .downloads] | @tsv'
# other stats: https://pypistats.org/api/
