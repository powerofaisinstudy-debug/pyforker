# PyForker Bot

PyForker Bot is the GitHub automation bot for the PyForker project.

It runs on a server and helps automate repository maintenance.

## Current Features

- Automatically responds to new issues
- Adds appropriate GitHub labels
- Posts automated comments
- Runs independently using a dedicated GitHub bot account

## How It Works

GitHub
  ↓
PyForker Bot
  ↓
Analyze issue
  ↓
Apply labels
  ↓
Post response

## Example

When an issue is opened:

> Import rewriting fails with relative imports

PyForker Bot can identify it as:

- `bug`
- `import-rewriting`

and automatically apply those labels.

## Future Plans

### PyForker-MergerBot

A future bot will handle pull-request automation, including:

- PR checks
- Merge requirements
- Merge readiness
- Automated merging when configured

## Philosophy

PyForker Bot is designed to keep PyForker development simple,
automated, and maintainable.
