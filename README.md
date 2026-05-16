# nostr-post skill

OpenClaw / AgentSkill for publishing public Nostr kind-1 text notes through [`nak`](https://github.com/fiatjaf/nak).

## What it does

- Drafts short Nostr posts
- Defaults to English
- Uses Hungarian when requested or when source material is Hungarian
- Publishes with `nak` using an `nsec` from `NOSTR_NSEC` or `~/.nostr/config.json`
- Supports configurable relay lists

## Files

- `nostr-post/` — source skill folder
- `nostr-post.skill` — packaged skill archive

## Security

Do **not** commit real `nsec` keys. The included config snippets use placeholders only.
