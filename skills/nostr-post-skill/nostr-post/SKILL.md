---
name: nostr-post
description: Post public kind-1 text notes to Nostr relays. Use when the user asks to post, publish, announce, share, or cross-post something on Nostr, including Hungarian triggers like "posztolj nostr-re", "küldd ki nostr-re", or when preparing Nostr announcements from chat, summaries, links, project updates, or short thoughts. Defaults to English unless the user explicitly asks for Hungarian or the source material is Hungarian.
---

# Nostr Post

Post public kind-1 Nostr text notes with `nak` via `scripts/post_nostr.py`.

## Safety

- Treat Nostr posts as public and hard to retract.
- Never reveal, print, commit, or paste an `nsec` private key.
- Do not post private chats, secrets, credentials, unfinished drafts, or internal operations.
- If the user provides exact final post text and explicitly asks to post it, publish it.
- If the content needs rewriting or the intent is ambiguous, draft first and ask for confirmation before publishing.

## Language

- Default to English.
- Use Hungarian when the user asks in Hungarian, asks for Hungarian, or the source material is Hungarian.
- If source material is mixed, match the audience and ask only if unclear.

## Setup

Requires `nak` on PATH. `nak` is preferred because it signs events, calculates the event ID, and broadcasts to relays without custom Nostr signing code.

Install examples:

```bash
# macOS
brew install nak

# Go toolchain
go install github.com/fiatjaf/nak@latest
```

Store the private key in one of these places:

1. Environment variable: `NOSTR_NSEC`
2. Config file: `~/.nostr/config.json`

Example config:

```json
{
  "nsec": "nsec1...",
  "relays": ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.primal.net"]
}
```

Optional relay override:

```bash
export NOSTR_RELAYS='wss://relay.damus.io,wss://nos.lol,wss://relay.primal.net'
```

## Drafting guidance

- Keep posts short, ideally under 500 characters.
- Put the hook in the first line.
- Link to full content instead of pasting long text.
- Preserve hashtags, npubs, note IDs, and links when useful.
- For Bitcoin/RaspiBlitz/OpenClaw updates, be direct and technical; avoid corporate tone.

## Publish

From this skill directory:

```bash
python3 scripts/post_nostr.py "Your note text here"
```

Or pipe content:

```bash
python3 scripts/post_nostr.py < /path/to/content.txt
```

Dry-run before posting if unsure:

```bash
python3 scripts/post_nostr.py --dry-run "Your note text here"
```

Use custom relays for one post:

```bash
python3 scripts/post_nostr.py --relay wss://relay.damus.io --relay wss://nos.lol "Your note text here"
```

## After publishing

- Report the note ID if available.
- If the tool returns relay-specific errors, summarize them without exposing secrets.
