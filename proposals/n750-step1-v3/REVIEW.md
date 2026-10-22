# N750 selection and qualification — proposed scope

Recovered completed local evidence; no admission or freeze has occurred. This
packet uses the publisher merged in PRs #30/#31, without modifying that publisher.

750 qualified physical sources: five Treasury annual XML feeds (yield curve,
bill rates, long-term rate, real yield curve, real long-term rate; 2025) and
745 SEC Daily Master files. Total input: 269,323,425 bytes. All five Treasury
candidates passed physical qualification; parsing was not run. `roster.json`
retains exact physical IDs, paths, hashes, sizes, publisher URLs and receipt pins.
`qualification.json` references the retained completed qualification evidence.

`plan.json` assigns proposed registrations SRC010451–SRC011200. Registered paths
are existing physical paths relative to the original repository; this does not
move or copy RAW. The recorded `admitted_at_utc` is a proposed registration
metadata timestamp, not evidence that publication occurred.

The unchanged frozen C750 is the baseline. The proposed union contains 1,500
physical identities with zero intersection; all 41 holdouts are excluded and
no outside-Universe sources are selected. The additive manifest preserves the
754 original v4 rows and appends 750 rows (1,504 total). The read-only production
planner validated the pinned baseline, Universe inventory and exact output scopes.
`grant.proposed.json` records all five admission and four freeze output hashes at
versioned destinations. `review-index.json` pins this packet and publisher code.

Retained remote checksum readback covers 450/750 selected sources. The remaining
300 are NOT claimed remotely verified; local qualification and remote availability
are distinct. No RAW upload, parser execution, processing or result freeze is
requested by this packet. Before publication, reconcile any required remote
prerequisite and obtain exact owner approval and trusted installation. All older
local grant drafts are obsolete; no grant in this directory is installed.

This selection PR is not `C1500_COHORT_PASS`. Step 2 remains unstarted. Day 4 PRs
merge into `day4/additive-m2`; main is reserved for Step 14.
