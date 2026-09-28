# DEC-001: Keep lab metadata at the repository root

- **Date:** 2026-09-28
- **Status:** decided
- **Context:** Each of the three published folders carried its own `AGENTS.md`, `.plicara/README.md`, `.plicara/project.yaml` and `.agents/skills/README.md`. The `AGENTS.md` copies repeated the root file with one boundary line changed, the skills READMEs were placeholders, and every folder had the same status. The lab now keeps one record per repository (foundation_lab DEC-003).
- **Decision:** Remove the per-folder copies. The root `project.yaml` stops listing child projects, declares the `gitskills-analysis` Python environment that its folder record declared, and keeps each folder's `published-snapshot-of` link under `related`. The rule that existed only in the folder copies, keeping claims traceable to local evidence, moves into the root `AGENTS.md`.
- **Consequences:** The folders no longer have their own lifecycle status or release IDs in metadata. The table below preserves each record as it stood before removal.

| Folder | ID | Name | Kind | Status | Description |
| --- | --- | --- | --- | --- | --- |
| `filter-censorship` | filter-censorship-release | Filter censorship public evidence | publication | maintained | Published evidence for the provider filtering article. |
| `gitskills-analysis` | gitskills-analysis-release | GitSkills public evidence | publication | maintained | Published analysis snapshot for the GitSkills series. |
| `jev-systemone` | jev-systemone-release | Jev public evidence | publication | maintained | Published evidence for the Jev decision article. |
