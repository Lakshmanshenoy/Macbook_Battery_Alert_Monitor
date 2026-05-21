## Contributing

Thanks for contributing. These conventions keep releases stable and automated.

### Commit message style

Use Conventional Commits:
- `feat: add automatic release workflow`
- `fix: correct threshold calculation`
- `chore(release): 1.2.3`
- `docs: update README`

Commit messages are enforced by:
- local Husky `commit-msg` hook (`commitlint`)
- CI commit lint workflow on pull requests

### Local setup (one-time)

```bash
npm ci
npm run prepare
bash setup.sh
```

### Developing and testing

```bash
python3 battery_alert_gui.py
bash scripts/checks.sh
```

### Pull requests

- Keep changes focused and include tests when practical.
- Open PRs against `main`.
- Ensure CI is green before requesting review.

### Releases

- Releases are automated with semantic-release on pushes to `main`.
- semantic-release determines version from commit messages (major/minor/patch), updates release files, generates changelog, tags, and publishes a GitHub release.
- Release tags trigger the macOS release build workflow.

### Important release-hook note

During semantic-release CI runs, Husky hooks are intentionally disabled (`HUSKY=0`) so the bot-generated release commit is not blocked by local `commit-msg` hook rules.

### If something fails

- If commit lint fails: fix commit messages and push again.
- If release fails: include workflow run logs and the target tag/version in your issue.
