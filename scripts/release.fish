#!/usr/bin/env fish

cd (dirname (status filename))/..

if test (count $argv) -eq 0
    echo 'Usage: scripts/release.fish "Description of changes"'
    exit 1
end

set note (string join " " -- $argv)

# Synchronize with GitHub.
git pull --rebase --autostash origin main; or exit 1

# Build the new release and update repository metadata.
python3 scripts/build_skin.py --bump-patch --note "$note"; or exit 1

# Publish everything.
git add -A; or exit 1
git commit -m "$note"; or exit 1
git push origin main; or exit 1

echo "Skin update published successfully."
