# C300 post-approval shallow execution

The user's subsequent approval activates exactly the 720 PASS bindings in packet
SHA-256 `3873e9d07e4bcc2f357f940d05cf4fc5dc1262358b641d1debba2ef117910e05`.
The original packet, registry, validation and checkpoint remain unchanged. A new
approval record preserves the actual authorization text, packet hash, exact binding
fingerprints and recording time; the original message timestamp remains unknown.
The other 12 FSDS num.txt bindings retain validation FAILED and execution BLOCKED.

`edp_lab.agents.post_approval_v1` adds a deterministic evidence-reuse execution path.
The host checks the sealed original checkpoint and all its artifacts, the exact
approved membership, original parser implementation hashes and frozen source
bindings. It rehashes each of the 300 current physical RAW instances once. Matching
parent hashes establish that the already hashed archive members are unchanged;
repeating decompression or parsing is unnecessary. No changed input is accepted.

The pure read-only Agent processes the approved bindings with their verified prior
mechanical results and full source/member/line/byte evidence. Each trace explicitly
says VERIFIED_EVIDENCE_REUSE. This is post-approval shallow execution over completed
full-member evidence, not a new RAW parse or full statistical profiling. The five
profiling adapters and GOLD's completed 13-table execution remain reused unchanged.

Evaluation independently assembles expectations from original discovery member
records, compares all 732 binding outcomes and complete reused mechanical results,
checks trace/report fingerprints, and replays the pure Agent without rereading RAW.
Runtime provenance and governance hashes are captured. Nondeterministic elapsed
time and peak resource measurements stay in a separate metrics artifact. Final
checks run once after implementation; previous checkpoints and failed evidence
remain intact. No semantic facts are promoted and no later study scope is added.

`metadata/section_2_6_checkpoint_v2.json` points to the new checkpoint and approval
hashes. Reproduction uses the preserved execution script and source snapshot under
its gitignored post-approval directory. The root AGENTS.md mission makes invariant
correctness, bounded evaluation and measured automation binding engineering goals.
