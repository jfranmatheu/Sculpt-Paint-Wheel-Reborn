: Sync only the ackit folder from upstream:
: First stash any existing changes
call git stash push --keep-index
call git fetch upstream
call git checkout main
: Remove existing ackit directory and clean Git's index
rd /s /q sculpt_plus\ackit
call git rm -r --cached sculpt_plus/ackit
call git commit -m "Remove ackit folder for sync"
: Read the new tree from upstream
call git read-tree --prefix=sculpt_plus/ackit upstream/main:ackit_addon_template/ackit
call git checkout-index -f -a
call git commit -m "Sync ackit folder from upstream"
: Restore any previously stashed changes
call git stash pop