if [[ $(git checkout test && git merge --ff-only test) ]]; then git push; else  if [[ $(git checkout test && git --no-pager log --merges test..test2) ]]; then exit 1; else git rebase test2 && git push; fi fi
