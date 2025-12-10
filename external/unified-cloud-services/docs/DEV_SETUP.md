# Pre-Commit Hooks Setup Guide

This guide helps new contributors set up pre-commit hooks to ensure consistent code quality across the team.

## What Are Pre-Commit Hooks?

Pre-commit hooks automatically run checks and formatting **before** you commit code. This catches issues early and ensures all team members follow the same standards.

## One-Time Setup

### 1. Install pre-commit

```bash
pip install pre-commit
```

Or if you're using the dev dependencies:

```bash
pip install -e .[dev]
```

### 2. Install the Git Hooks

Navigate to the project directory and run:

```bash
cd unified-cloud-services
pre-commit install
```

You should see: `pre-commit installed at .git/hooks/pre-commit`

### 3. (Optional) Test on Existing Files

Run the hooks on all files to ensure everything is properly formatted:

```bash
pre-commit run --all-files
```

## What Happens Now?

Every time you run `git commit`, the following checks will run automatically:

1. **Black Formatter** - Formats all Python code to maintain consistent style
2. **Trailing Whitespace** - Removes unnecessary whitespace at end of lines
3. **End of File Fixer** - Ensures files end with a newline
4. **YAML Syntax Checker** - Validates YAML files
5. **TOML Syntax Checker** - Validates TOML files (like pyproject.toml)
6. **Large Files Check** - Prevents files larger than 1MB from being committed

### If Checks Pass ✅
Your commit proceeds normally.

### If Checks Fail ❌
- **Auto-fixable issues** (like formatting): Files are automatically fixed and staged
  - You'll need to run `git commit` again
- **Non-fixable issues**: You must fix them manually before committing

## Common Workflows

### Normal Commit
```bash
git add .
git commit -m "Add new feature"
# Pre-commit runs automatically, may auto-fix files
# If files were modified, commit again:
git commit -m "Add new feature"
```

### Skip Hooks (Emergency Only)
```bash
git commit --no-verify -m "Emergency fix"
```
⚠️ **Use sparingly!** Skipping hooks should be rare and only for urgent situations.

### Run Hooks Manually
```bash
# Run on all files
pre-commit run --all-files

# Run on specific files
pre-commit run --files path/to/file.py

# Run specific hook only
pre-commit run black --all-files
```

### Update Hook Versions
```bash
pre-commit autoupdate
```

## Troubleshooting

### "command not found: pre-commit"
- Make sure you installed it: `pip install pre-commit`
- Check if it's in your PATH: `which pre-commit`

### "pre-commit not installed at .git/hooks/pre-commit"
- Run `pre-commit install` in the project directory

### Black is Reformatting Too Many Files
- This is normal if files weren't formatted before
- Run `pre-commit run black --all-files` once to format everything
- Future commits will only format changed files

### Hooks Are Running Too Slowly
- First run downloads dependencies, subsequent runs are faster
- You can skip hooks temporarily with `--no-verify` (not recommended)

## Customization

The hook configuration is in `.pre-commit-config.yaml`. To modify:

1. Edit the file (requires team agreement)
2. Update hooks: `pre-commit install --install-hooks`
3. Test: `pre-commit run --all-files`

## Configuration File Location

```
unified-cloud-services/
├── .pre-commit-config.yaml  ← Hook configuration
└── pyproject.toml           ← Black settings (line-length, etc.)
```

Black formatting rules are defined in `pyproject.toml` under `[tool.black]`.

## Team Standards

- **All team members must install pre-commit hooks**
- Do not skip hooks unless absolutely necessary
- If hooks are failing, fix the code (don't force commit)
- Keep `.pre-commit-config.yaml` up to date

## Questions?

If you encounter issues or have suggestions for additional hooks, please reach out to the team lead or create an issue in the repository.
