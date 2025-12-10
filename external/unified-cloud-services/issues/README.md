# Issues Tracker

This directory tracks issues, problems, and resolutions encountered during development sessions.

## Format

Each issue file follows the naming pattern:
```
YYYY-MM-DD-short-description.md
```

## Issue Status

- ✅ **Resolved** - Issue has been fixed and verified
- ⚠️ **Action Required** - Issue identified, action needed
- 🔄 **In Progress** - Issue being worked on
- 📋 **Pending** - Issue documented, awaiting resolution

## Current Issues

### 2025-01-15 Session

1. **Structure Refactor Import Issues** (`2025-01-15-structure-refactor-import-issues.md`)
   - Status: ✅ Resolved
   - Import path issues after moving services to `app/core/`

2. **Services Directory Removal** (`2025-01-15-services-directory-removal.md`)
   - Status: ✅ Resolved
   - Removed `services/` directory, aligned with instruments-service structure

3. **Instruments Domain Bucket Creation** (`2025-01-15-instruments-domain-bucket-creation.md`)
   - Status: ⚠️ Action Required
   - Need to create GCS buckets and BigQuery dataset for instruments domain

4. **Archive Usage Audit** (`2025-01-15-archive-usage-audit-needed.md`)
   - Status: ⚠️ Pending Verification
   - Verify no active code depends on archived functionality

## How to Use

1. **Create New Issue**: Create a new markdown file with date and description
2. **Update Status**: Update status as work progresses
3. **Link to PRs**: Reference pull requests or commits that resolve issues
4. **Archive Resolved**: Move resolved issues to `issues/resolved/` if desired

## Related Documentation

- `docs/` - Architecture and design documentation
- `market-tick-data-handler/docs/` - Service-specific documentation
