# Releasing `glstring` to PyPI

Publishing uses **PyPI Trusted Publishing (OIDC)** via the
`.github/workflows/release.yml` workflow. No API tokens are stored anywhere.

## One-time setup: register the PyPI pending publisher

Before the first release, a PyPI maintainer must add a **pending trusted
publisher** so the project can be created on first publish.

### PyPI (https://pypi.org/manage/account/publishing/)

Add a new pending publisher with **exactly** these values:

| Field                     | Value                           |
|---------------------------|---------------------------------|
| PyPI Project Name         | `glstring`                      |
| Owner                     | `societyforimmunepolymorphism`  |
| Repository name           | `py-glstring`                   |
| Workflow name             | `release.yml`                   |
| Environment name          | `pypi`                          |

### TestPyPI (recommended dry run first, https://test.pypi.org/manage/account/publishing/)

Same values as above. To exercise the dry run, temporarily point the publish
step at TestPyPI (`with: repository-url: https://test.pypi.org/legacy/`) on a
branch, or add a separate `testpypi` environment + publisher.

## Cutting a release

1. Bump `version` in `pyproject.toml` (e.g. `0.1.0`).
2. Commit and tag: `git tag v0.1.0 && git push origin v0.1.0`.
3. Create a **GitHub Release** for that tag (Releases -> Draft a new release ->
   choose the tag -> Publish).
4. Publishing the release triggers `release.yml`, which builds the sdist/wheel,
   runs `twine check`, and publishes to PyPI via OIDC.

The GitHub Actions **Environment** `pypi` can optionally be configured with
required reviewers so a human must approve each publish.

## Notes

- Distribution/import name is `glstring` (repo is `py-glstring`).
- The parser and AST have zero runtime dependencies.
- Publishing is irreversible (a version cannot be re-uploaded). Prefer a
  TestPyPI dry run for the first release.
