## Contributing

Thanks for contributing! A few repository conventions and quick setup steps so releases stay smooth.

1) Commit message style — Conventional Commits

- Use Conventional Commits for commit messages. Examples:
  - `feat: add automatic release workflow`
  - `fix: correct threshold calculation`
  - `chore(release): 1.2.3`
  - `docs: update README`

- This repository enforces commit message linting via `commitlint` and a Husky `commit-msg` hook. PRs will also be checked by CI.

2) Local setup (one-time)

Run this once to install Node dev tools and enable Husky hooks:

```bash
npm ci
npm run prepare
```

3) Making commits

- Make your changes on a feature branch, write a Conventional Commit message, and push a PR to `main`.
- The `commit-msg` hook will validate locally; CI will run `commitlint` on the PR.

4) Releases

- Releases are automated using `semantic-release` on pushes to `main`.
- Semantic-release reads commit messages to determine the next semantic version (major/minor/patch), updates `pyproject.toml` and `src/battery_alert/constants.py`, generates `CHANGELOG.md`, creates a release tag, and publishes a GitHub Release.
- The tag triggers the release build workflow to produce the signed/notarized DMG and publish artifacts.

5) If something fails

- If CI fails the commitlint step, amend your commits to follow Conventional Commits and push again.
- If the release workflow fails, contact the maintainers and include the workflow logs and the tag name.

Thanks — your contributions keep this project healthy and releasable.
# Contributing

Thanks for your interest in contributing. Suggested small ways to help:

- File issues for bugs or feature requests.
- Test releases on different macOS versions and report results.
- Review code in the repository and submit pull requests.

Testing locally
- Create a Python virtualenv and run `bash setup.sh`.
- Run `python3 battery_alert_gui.py` to sanity-check the app.

Code style and tests
- Keep changes small and focused; include tests where practical.
