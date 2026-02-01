# Auto-Save: Two-Phase Memory Capture

Stop Hook uses a **Fast + Slow** dual-phase architecture.

## Phase 1: Fast Path (<1s, sync)

Regex-based pattern matching for immediate capture:

| Pattern Type | Examples | Min Weighted Length |
|--------------|----------|---------------------|
| Preferences | `I prefer...`, `I like...`, `偏好...` | 10 |
| Decisions | `decided to use...`, `chose...`, `決定...` | 10 |
| Discoveries | `discovered...`, `found that...`, `solution is...` | 10 |
| Learnings | `learned...`, `root cause...`, `the issue was...` | 10 |
| Facts | `work at...`, `live in...` | 10 |
| No pattern | General content | 35 |

Also extracts **conclusion markers** from Claude's responses:
- `Solution`, `Discovery`, `Conclusion`, `Recommendation`, `Root cause`
- `解決方案`, `發現`, `結論`, `建議`, `根因`

> **Weighted length**: CJK chars × 2.5 + other chars × 1

## Phase 2: Slow Path (5-15s, async)

Background LLM analysis using Claude CLI:

- Runs in detached subprocess (doesn't block Claude Code)
- Analyzes last 6 user + 4 assistant messages
- Extracts up to 5 memories with type/confidence
- Memory types: `discovery`, `decision`, `learning`, `preference`, `fact`
- Logs to `~/.cache/kiroku-memory/llm-worker.log`

## Deduplication

Both phases share a 24-hour TTL deduplication cache.

## Filtered Out (Noise)

- Short responses: `OK`, `好的`, `Thanks`
- Questions: `What is...`, `How to...`
- Errors: `error`, `failed`
