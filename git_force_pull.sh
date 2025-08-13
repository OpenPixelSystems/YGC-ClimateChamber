#!/bin/bash

# Ensure we're inside a git repo
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "This is not a Git repository."
    exit 1
fi

# Fetch the latest data from all remotes and clean stale branches
git fetch --all --prune

# Get all remote branches (exclude HEAD pointer)
branches_raw=$(git for-each-ref --format='%(refname:short)' refs/remotes/origin | grep -v 'HEAD')

# Create menu options with latest commit messages
options=()
branches=()

echo "Available remote branches:"
index=1
while IFS= read -r branch_ref; do
    branch_name="${branch_ref#origin/}"

    # Use the updated origin/<branch> to get the latest commit message
    commit_msg=$(git log -1 --pretty=format:"%s" "origin/$branch_name")

    options+=("$branch_name - \"$commit_msg\"")
    branches+=("$branch_name")
    echo "  [$index] ${branch_name} - \"$commit_msg\""
    ((index++))
done <<< "$branches_raw"

# Prompt user to select a branch
read -p "Select a branch number to pull and hard reset: " selection

# Validate input
if ! [[ "$selection" =~ ^[0-9]+$ ]] || ((selection < 1 || selection > ${#branches[@]})); then
    echo "Invalid selection."
    exit 1
fi

selected_branch="${branches[selection-1]}"
echo "You selected: $selected_branch"

read -p "This will discard ALL local changes and hard reset to '$selected_branch'. Continue? (y/n): " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo "Resetting to origin/$selected_branch..."
    git fetch origin
    git checkout "$selected_branch" 2>/dev/null || git checkout -B "$selected_branch" "origin/$selected_branch"
    git reset --hard "origin/$selected_branch"
    echo "Reset complete."
else
    echo "Operation canceled."
fi

