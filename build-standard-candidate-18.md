# Build Standard candidate — point 18

*Drafted for review before merging into BUILD-STANDARD-v2.md. Same format as points 8–17: a rule,
and the real incident that made it a rule.*

## 18. A decisions file only governs the session that has the current copy of it

**The rule:** before a coding session starts real work, confirm the decisions file it just read is
the same one the last session wrote — not "probably close enough." If a chat-side conversation
resolved anything since the file on disk was last saved, get that resolution onto disk first. When
in doubt, paste the chat-side file over the disk copy before typing the first instruction.

**Why this is now a rule.** A planning conversation resolved three items — which module layout to
build into, an output-validator's error-handling behavior, and whether to route builds through an
alternate backend — writing them into a decisions file that existed only in that conversation's own
workspace. That file was never downloaded back onto the machine actually running the coding tool.
A separate coding session then started, read the decisions file that was actually on disk — which
still showed those three items unresolved — and, working correctly from what it could see, re-asked
one of them from scratch and assigned fresh IDs to its own new items. Those fresh IDs turned out to
be the exact IDs the planning conversation had already used for the resolved items nobody had told
it about. Two files, both internally consistent, silently diverging — the identical failure shape
this project's own classical citation work had already documented and fixed once, in a different
document, for a different reason (register items colliding across independent retrieval passes).
The fix there was a numbering crosswalk after the fact. The fix here is not letting it happen: a
decisions file is single-source-of-truth in name only if two tools can each hold a copy and neither
one is required to be current before it starts writing new decisions into it.

**Practical version:** if the coding tool and the planning conversation are different programs (a
chat interface and a local CLI tool, say), decisions live in a file that has exactly one location,
and every session — chat or code — starts by confirming it has that location's current content, not
a copy from before the last edit. If a project is in git, this is nearly free: commit the decisions
file after every session that touches it, and the next session's first move is `git pull` or
equivalent before it reads anything. If it isn't in git yet, that absence is itself worth naming as
the thing to fix, ahead of the next multi-session build.
