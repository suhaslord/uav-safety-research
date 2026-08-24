# AIEA High-School Intern Profile — PR Ready

Professor Leilani Gilpin approved adding this profile to the AIEA Lab website on August 22, 2026.

## Target website file

Create this file in the AIEA website fork at:

`content/intern/suhas.md`

```toml
+++
bio = "Suhas Beemineni is a high school student interested in aerospace engineering, autonomous systems, and AI safety. His independent research project, AegisLand, studies reproducible simulation-based validation for UAV autonomy using PX4 and Gazebo, with an emphasis on uncertainty, failure and recovery behavior, provenance, and evidence-bounded safety claims."
date = "2026-08-23"
id = "suhas_beemineni"
interests = ["Safe Autonomous Systems", "UAV Autonomy", "Simulation-Based Validation", "AI Safety and Explainability", "Fault Detection and Recovery"]
name = "Suhas Beemineni"
portrait = "/portraits/default.jpg"
short_bio = "High school intern researching reproducible UAV autonomy validation and uncertainty-aware safety evaluation"
short_name = "Suhas"
title = "High School Intern"

[[social]]
    icon = "github"
    icon_pack = "fa"
    link = "https://github.com/suhaslord"

[[education]]
    course = "High School"
    institution = "River Islands High School"
    year = 2029

[[organizations]]
    name = "UC Santa Cruz"
    role = "High School Intern"
+++

I am working on AegisLand, a simulation-only PX4/Gazebo research project focused on rigorous UAV autonomy validation. I am especially interested in how autonomous systems can report uncertainty honestly, recover from degraded sensing, and preserve clear boundaries between simulation evidence and real-world safety claims.
```

## Project

AegisLand: https://github.com/suhaslord/uav-safety-research

## PR metadata

**Branch:** `suhas-intern-profile`

**Title:** `Add Suhas Beemineni intern profile`

**Body:**

```markdown
Adds my AIEA Lab high school intern profile as part of onboarding.

- Added `content/intern/suhas.md`
- Uses the site's default portrait for now
- Includes my research interests, education, GitHub, and AegisLand work
```

## Submission process verified

Recent AIEA intern-profile submissions use a personal fork of `aiea-lab/aiea-lab.github.io`, commit the profile under `content/intern/` (and optionally a portrait under `static/img/portraits/`), then open a pull request back to `aiea-lab:main`.

## Current blocker

The connected GitHub integration can read the AIEA website repository but cannot create a branch there (`403 Resource not accessible by integration`) and exposes no fork action. No `suhaslord/aiea-lab.github.io` fork currently exists. Once that fork exists, the branch, file, and PR can be created through the connected GitHub tools.
