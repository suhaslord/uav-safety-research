# GitHub Pages

The `github-pages.yml` workflow publishes website changes pushed to `main`.
The research records remain in their existing source files. The build creates
static files for all 26 phase routes and prefixes internal links and assets with
the GitHub project path.

One-time repository setup: open **Settings → Pages**, then select **GitHub
Actions** as the build and deployment source. This requires repository
administration access; the workflow's `GITHUB_TOKEN` cannot enable Pages itself.
After enabling it, run **Publish AegisLand to GitHub Pages** from the Actions tab.
Later website changes on `main` deploy automatically.

Site address: https://suhaslord.github.io/uav-safety-research/

To build locally from the repository root:

```sh
node deploy/vercel/fetch-editorial-media.mjs
python deploy/github-pages/build.py
```

The generated site is in `_pages/`. The workflow downloads the credited NASA
photographs before building; the short, credited NASA film is tracked in Git.
