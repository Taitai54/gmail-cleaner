# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Email Preview**: Preview emails before deletion to avoid accidental data loss
- **Result Persistence**: Scan results cached in browser localStorage, survive page refreshes
- **Error Tracking**: Track and report partial failures in batch operations
- **Failed Email Count**: Display count of emails that couldn't be processed during scans
- **Enhanced Confirmations**: Detailed confirmation dialogs showing affected email counts and date ranges
- **Toast Notifications**: Non-intrusive success/error notifications throughout the app
- **Filter Badge**: Visual indicator showing number of active filters
- **Accessibility Improvements**: Added ARIA labels and improved keyboard navigation
- **Better Loading States**: Clear feedback when operations are already in progress
- CodeRabbit AI code review integration with `.coderabbit.yaml` configuration
- Pre-commit hooks for code quality checks (ruff, bandit, trailing whitespace, etc.)
- Comprehensive type annotations throughout the codebase

### Changed
- Improved error handling with detailed error messages and logging
- Enhanced batch operation callbacks to track failures
- Updated UI feedback for all long-running operations
- Better confirmation dialogs with detailed statistics
- Updated pre-commit hook versions to latest stable releases
- Improved code formatting consistency (double quotes, trailing commas, whitespace)
- Enhanced function signatures with multiline formatting for better readability
- Normalized code style across Python, JavaScript, CSS, and HTML files

### Fixed
- Silent failures in batch operations now logged and reported
- Missing user feedback when operations are already in progress
- Timezone handling in CSV filename generation (now uses UTC)
- Missing return type annotations in multiple functions
- Closure variable binding in batch callback functions
- Test coverage improvements with proper mock assertions
- Boolean positional argument pattern in `mark_important_background`

## [1.0.0] - 2024-11-29

### Added
- Initial release
- Bulk unsubscribe functionality with one-click support
- Delete emails by sender with bulk operations
- Mark emails as read in bulk
- Smart filtering options (age, size, category, sender, label)
- Docker support for all platforms
- Gmail API integration with batch requests
- Privacy-first architecture (runs 100% locally)
- Gmail-style user interface
- Label management (create, apply, remove)
- Archive emails functionality
- Mark emails as important/unimportant
- Download emails as CSV export

[Unreleased]: https://github.com/Gururagavendra/gmail-cleaner/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Gururagavendra/gmail-cleaner/releases/tag/v1.0.0
