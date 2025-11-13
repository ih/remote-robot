---
description: Update docs if stale, commit all changes with descriptive message, and push to GitHub
---

# Commit All Changes and Push

Review all uncommitted changes, update documentation if needed, create a comprehensive commit, and push to GitHub.

## Steps

1. **Check git status**: Review all modified, added, and deleted files
2. **Check documentation freshness**:
   - Find when README.md and CLAUDE.md were last updated
   - Review commits since last doc update
   - If significant changes exist, update both documentation files
3. **Stage all changes**: Add all modified files to staging
4. **Create commit**: Write a comprehensive commit message that:
   - Summarizes what changed (features, fixes, refactors, etc.)
   - Lists key changes in bullet points
   - Includes "🤖 Generated with [Claude Code](https://claude.com/claude-code)" footer
   - Includes "Co-Authored-By: Claude <noreply@anthropic.com>"
5. **Push to GitHub**: Push the commit to the remote repository

## Important

- Review all changes before committing to ensure nothing sensitive is included
- Update docs comprehensively if they're stale (not just current session changes)
- Create descriptive commit messages that explain the "why" not just the "what"
- Verify push succeeds and check for any merge conflicts
