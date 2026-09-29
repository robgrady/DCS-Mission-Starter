# Contact & feedback — requirements and implementation plan

*Proposal for review, 13 Aug 2026. Nothing built yet.*

Rob's ask: a contact form reachable from the footer and the top-right, taking
name, email and comment; submissions land in the admin section and carry a
read / unread state.

---

## 1. What this is actually for

This is the product's **only inbound channel**. Everything else in the app is
one-way: we hand out missions and never hear back. The analytics ledger
records what missions people *build*, deliberately never who they are — so it
can tell us the Hornet is popular and can never tell us the Syria map
crashed for someone on Tuesday.

That shapes the design. The form is not a support desk; it is a low-friction
way for a pilot to say "this broke" or "add the Viggen" while the thought is
fresh. Optimising for volume of *useful* signal beats optimising for
completeness of *record*.

Three consequences, each argued below: **email is optional**, **there is a
topic selector**, and **context is captured automatically**.

## 2. UX requirements

### 2.1 Entry points

- **Top bar, right side**: "Contact" as a quiet text link beside User guide /
  What's new / Roadmap. It belongs in that set — those are the site's
  meta-links, and this is one.
- **Footer**: the same link. Footer placement is where people look *after*
  something has gone wrong, which is exactly when they want it.
- Both open the same modal. No separate page, no navigation away from a
  half-configured mission — losing an in-progress Builder state to a bug
  report would be a self-inflicted wound.

### 2.2 The form

| Field | Required | Notes |
|---|---|---|
| Name | Yes | Free text, 1–80 chars. No "first/last" split — over-collection. |
| Email | **No** | If given, validated and used only to reply. The label says so. |
| Topic | Yes | Select: Bug report · Feature request · Mission/content idea · Something else. Defaults to unset so the choice is deliberate. |
| Comment | Yes | Textarea, 10–4000 chars, live counter past 3500. |

**Why email is optional.** Requiring it costs submissions from people who
just want to report a bug and never hear from us again — the single most
valuable message type. Making it optional and *explaining the trade* ("Only
if you'd like a reply — we won't use it for anything else") gets both the
anonymous bug reports and the addresses of people who actually want contact.

**Why a topic selector.** It costs the user one click and buys the admin
inbox a filter axis and a triage order. Without it, every message must be
opened to be classified.

### 2.3 Auto-captured context (shown to the user before sending)

A bug report without a version number is half a bug report. On submit we
attach: **app version**, **which view they were on** (entry / quick /
library / builder), and **their current recipe code if the Builder has one**.

This is disclosed, not silent: a collapsed "What we'll include" line the user
can expand and read. It contains no personal data — the recipe code is a
mission configuration, the same string share links already publish.

### 2.4 Submission flow

1. Client-side validation, inline errors tied to fields via `aria-describedby`.
2. Submit disables the button and announces "Sending…" in a live region.
3. Success replaces the form body with a confirmation naming what happens
   next ("We read everything. If you left an email we'll reply when there's
   something worth saying."). Failure keeps the typed text and offers retry —
   never destroy a message someone spent five minutes writing.

### 2.5 Accessibility (non-negotiable — we just shipped AA)

Reuses the `modalOpen`/`modalClose` focus trap from v1.63.0: `role="dialog"`,
`aria-modal`, focus to the first field, Escape closes, focus restored to the
link that opened it. Every field label bound via `for`/`id`. Errors announced
via `role="alert"`. The submit status is a live region. The new markup must
pass the existing axe gate — which the release will run automatically.

## 3. Anti-abuse

A public unauthenticated write endpoint is a spam magnet. Three layers, no
CAPTCHA (they are an accessibility and privacy tax, and the ADA-adjacent
standard we just adopted frowns on them):

1. **Honeypot field** — a hidden input real users never fill. Bots fill
   everything. Silently accept-and-discard so the bot sees success and stops
   retrying.
2. **Time-to-submit floor** — a form completed in under ~3 seconds was not
   typed by a human. Signed timestamp issued with the form, checked on submit.
3. **Rate limit** — per-IP, in-memory token bucket (5/hour, 20/day). The IP is
   used for the limiter's key only and is **never written to disk**, which
   keeps the project's no-PII analytics stance intact.

Plus hard caps: 4 KB body limit, field-length validation server-side, and
HTML-escaping on render in the admin (the admin renders user-controlled
strings — this is the one place an XSS could land).

## 4. Data model and storage

Follows the analytics module's proven pattern: **JSONL on the Fly volume**, one
file per month, no database. It survives deploys, is trivially greppable, and
adds no new infrastructure.

```
CONTACT_DATA_DIR (default ./instance/contact, on Fly: /data/contact)
  messages-202608.jsonl
```

One JSON object per line:

```json
{
  "id": "01J8Z...",           // ULID: sortable by time, unique, no counter file
  "ts": "2026-08-13T12:04:11Z",
  "name": "…", "email": "…|null", "topic": "bug",
  "comment": "…",
  "context": {"version": "1.63.0", "view": "builder", "recipe": "…|null"},
  "read": false,
  "read_at": null
}
```

**On mutating read state in an append-only file**: we append a
`{"id": ..., "op": "read"}` record rather than rewriting the line, and fold
the ops when loading. Rewriting a JSONL line in place is where data loss
lives, and the volume is single-writer so ordering is guaranteed.

**Retention**: messages older than 24 months are prunable by a documented
command. Not automatic — deleting someone's bug report on a timer is a
decision, not a default.

## 5. API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/contact/token` | none | Issues the signed form timestamp (anti-bot) |
| `POST` | `/api/contact` | none | Submit. 202 on accept, 422 on validation, 429 on rate limit |
| `GET` | `/admin/contact` | admin cookie | Inbox list |
| `POST` | `/admin/contact/{id}/read` | admin cookie | Toggle read/unread |
| `POST` | `/admin/contact/{id}/delete` | admin cookie | Delete (append a tombstone op) |

`/api/contact` returns a deliberately generic success for honeypot and
time-floor rejections — telling a bot why it failed helps the bot.

## 6. Admin inbox

A fourth tab in the existing bar: `Sponsor ads · Mission packs · Analytics ·
**Contact**`, with an **unread count badge** — the tab is useless if you have
to open it to discover there is nothing new.

- **List view**, newest first: unread rows visually distinct (left accent
  border + bold, not color alone — same redundancy rule as the rest of the
  product). Each row shows date, topic chip, name, email-present indicator,
  and the first ~100 chars of the comment.
- **Filters**: All / Unread / by topic.
- **Expand a row** to read the full comment, the captured context, and a
  `mailto:` reply link pre-filled with a subject line — Rob replies from his
  own mail client; the app never sends email, which keeps us out of
  deliverability and spam-compliance territory entirely.
- **Opening a message marks it read**; an explicit "Mark unread" restores it
  (the "I'll deal with this later" action every inbox needs).
- Everything HTML-escaped on render.

**Reachability**: `/admin` is disabled unless `ADMIN_PASSWORD` is set — an
existing guard this feature inherits and must not weaken.

## 7. Privacy posture

The project's stated stance is "no PII leaves". A contact form *deliberately*
collects PII, so the stance needs an honest amendment rather than a quiet
exception:

- The form states, at the point of entry, what is stored and why.
- Email is optional and single-purpose (replying).
- IP is used transiently for rate-limiting and never persisted.
- Contact data lives in its own file tree, entirely separate from the
  analytics ledger, so the anonymous ledger stays anonymous.
- The privacy note in the footer/guide gets a paragraph covering this.

## 8. Test plan

- **Validation**: each field's bounds, both edges; email optional-but-valid.
- **Anti-abuse**: honeypot filled → accepted-and-discarded (nothing written);
  submit under the time floor → discarded; rate limit → 429 on the 6th.
- **Storage**: round-trip write/read; read-op folding produces the right
  state; a corrupt line doesn't take down the inbox (skip and continue).
- **Admin auth**: every `/admin/contact*` route 302s to login when
  unauthenticated — and this gets mutation-proven by removing one guard.
- **XSS**: a message containing `<script>` and `"><img onerror=...>` renders
  escaped in the inbox.
- **Accessibility**: the axe gate covers the modal automatically; plus a
  static scan that the new fields are labelled and the dialog is trapped.
- **No-PII**: assert the analytics ledger contains no contact fields — the
  two stores must not bleed.

Every guard mutation-proven, per standing practice.

## 9. Phasing

| Phase | Contents | Size |
|---|---|---|
| **1** | Storage module + API + form modal + both entry points + anti-abuse | one release |
| **2** | Admin inbox tab: list, filters, expand, read/unread, delete, badge | same release if it stays tight, else the next |
| **3** | Polish: mailto reply templates, CSV export, retention command | later, demand-gated |

Recommend shipping 1+2 together — a form whose messages nobody can read is
not a feature.

## 10. Open questions for Rob

1. **Notification**: should a new message do anything besides sit in the
   inbox? Options: nothing (check the tab), or a simple daily digest to a
   configured address via an SMTP env var. Nothing is the honest default;
   the digest is the one that gets messages actually read.
2. **Topic list**: are the four categories right for what you expect to
   receive?
3. **Retention**: 24 months a reasonable prune horizon?
