# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- The project hooks in `.claude/settings.json` refresh the auto-snapshot in Handsover.md on every
  Stop and before compaction. They do not write the narrative: you still update
  `# CURRENT STATE` in Handsover.md and TASKS.md yourself (AGENTS.md §7).
- Shell: Windows. In the Bash tool, backslashes inside heredocs can be altered — use the Edit/Write
  tools for code containing `\n`, regexes or Windows paths. Use PowerShell `Start-Process` for
  anything long-running (server, evals).
- Verify the real listener before stopping a process:
  `Get-NetTCPConnection -LocalPort 786 -State Listen` → check its command line contains `uvicorn app.main:app`.
- The user's preferences (auto-memory): complete, respectful, cited answers; never a false refusal;
  keep all docs current; reply in simple Hinglish.
