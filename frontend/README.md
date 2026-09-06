# ILUSIEBIS GAReshe — Reader

"Stories that reveal the reader." The minimal, polished web reading
experience — the first thing a real reader interacts with, per the
product spec's own "1 polished reader" priority.

## Setup

npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at your Django backend
npm run dev

Requires the Django backend (see the backend repo) running with at
least one Story whose StoryVersion is published and has a root_node set,
and a user account to log in with.

## What's here

- `/` — sign in (JWT against the Django backend)
- `/library` — published stories, hairline-divided list
- `/read/[storyId]` — the reading loop: prose → interpretation choice →
  next node → ... → ending → reflection → replay → run comparison

## Design system

Dark, editorial, single reading column. Colors and fonts are defined as
Tailwind tokens in `tailwind.config.js` (`ink`, `surface`, `parchment`,
`muted`, `brass`, `slate`) rather than Tailwind's defaults — `brass` is
reserved for moments of psychological insight only (interpretation
evidence, replay CTA); `slate` only ever marks "the other run" in a
comparison. Story prose renders in Noto Serif Georgian (handles
Mkhedruli correctly); UI chrome uses Inter.

## Known limitation

`next/font/google` fetches font files from Google Fonts at build time.
If you're building in a fully offline/restricted network environment,
either allow `fonts.googleapis.com` + `fonts.gstatic.com`, or switch to
`next/font/local` with self-hosted font files.

## Not yet built

Bookmark UI, typography/reading-comfort settings, the "Story Analysis"
flow-diagram visualization, and the marketing/discovery pages beyond a
bare list. All are additive — the reading loop itself doesn't change
under them.
