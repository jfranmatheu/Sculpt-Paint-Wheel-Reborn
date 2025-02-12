: Sync only the ackit folder from upstream:
call git fetch upstream
call git checkout main
: Remove existing ackit directory to avoid conflicts
rd /s /q sculpt_plus\ackit
call git read-tree --prefix=sculpt_plus/ackit upstream/main:ackit_addon_template/ackit
call git commit -m "Sync ackit folder from upstream"
