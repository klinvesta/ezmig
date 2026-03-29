# Deployment

This project uses an automated release workflow in `.github/workflows/release.yml` powered by `python-semantic-release`.

## What the workflow does

- runs tests with `uv run pytest`
- inspects commit messages on `dev` and `main` using Conventional Commits
- bumps `project.version` in `pyproject.toml`
- updates `docs/changelog.md`
- creates the release commit, Git tag, and GitHub release
- builds package artifacts with `uv build`
- publishes to PyPI
- builds and uploads standalone binaries

## Release rules

`python-semantic-release` determines the next version from commit messages:

- `feat:` → minor bump
- `fix:` / `perf:` → patch bump
- `BREAKING CHANGE:` or `!` in the type/scope → major bump
- `docs:`, `chore:`, `build:`, `style:`, `refactor:`, `test:` do not trigger a release

While EZMig is still in the `0.x` phase, breaking changes remain within `0.x` (`major_on_zero = false`).

Branch release channels:

- `dev` branch → prerelease channel with `-beta.N` versions
- `main` branch → stable releases

To keep development flow simple, all contributions should be merged into `dev` first. Promote to `main` when ready for stable release.

## Configure publishing

Use one of:

- **Recommended:** PyPI Trusted Publishing (OIDC)
- **Alternative:** repository secret `PYPI_API_TOKEN`
- If branch protection blocks `GITHUB_TOKEN` from pushing release commits/tags, create a `RELEASE_TOKEN` secret with `contents:write` access and the workflow will use it automatically.

## Normal release flow

No manual version bump or tag creation is needed.

1. Merge Conventional Commit messages into `dev` for prereleases
2. Promote `dev` to `main` for stable releases
3. The workflow calculates the next version
4. It writes the version/changelog updates and creates `vX.Y.Z`
5. It publishes the package and binaries automatically

Because the repository does not currently have historical release tags, the first automated run will bootstrap the tag history from the current `project.version` and create `v0.1.0`.

## Manual prereleases

Use `workflow_dispatch` when you want to force a prerelease.

Suggested inputs:

- `force`: `patch`, `minor`, or `major`
- `prerelease`: `true`
- `prerelease_token`: `beta`

This will create a SemVer prerelease such as `0.1.1-beta.1`.

> Note: `python-semantic-release` uses SemVer-style prereleases. If you need strict PEP 440 source versions like `0.1.1a1`, this tool is not a perfect fit.

## Local verification

Before enabling the workflow for real releases, test the configuration locally:

```bash
uvx --from python-semantic-release semantic-release --noop version
```

Then inspect the planned bump, tag, and changelog output.

## Build verification

```bash
uv build
```

Artifacts are written to `dist/`.
