---
description: Nightly review — verify today's notes, fix, relink, rebuild index.md
---

Run the nightly review of this knowledge base. Follow the rules in `CLAUDE.md`.

1. List everything added to `raw/` today and read today's `daily/` log and session notes.
2. For every wiki note created or changed today, check it against its source in `raw/`.
   Fix facts and quotes that don't match the source. Mark anything that can't be
   confirmed as `UNVERIFIED`. Never edit files in `raw/`.
3. Add what was missed: sources in `raw/` with no wiki page, and facts or quotes worth
   keeping that the pages left out.
4. Repair broken links across `wiki/` and make sure each page links to at least 2
   related pages with one line on why.
5. Rebuild `index.md`: one line per wiki page, linked, under 200 lines.
6. Do not delete or overwrite a whole note without the owner's yes. List merge or
   delete candidates instead.
7. Append a short entry to today's file in `daily/`.

Finish with exactly 3 lines:
- **Filed:** what was filed
- **Fixed:** what was fixed
- **Connection:** one connection the owner didn't see
