# Deploying to Fly.io

The app is a stateless FastAPI service; `fly.toml` and `Dockerfile` are in the
repo. **The Fly app is named `dcs-mission-starter`** (created by `fly launch`;
served at `dcs-mission-starter.fly.dev`). The app name is internal — it does not
affect the `sortiestarter.com` domain.

## First-time setup (already done)

```bash
brew install flyctl                 # macOS  (or: curl -L https://fly.io/install.sh | sh)
fly auth login
cd ~/Projects/DCS-Mission-Starter
fly launch --copy-config --no-deploy
fly deploy
fly open                            # curl https://dcs-mission-starter.fly.dev/api/health -> {"status":"ok",...}
```

Scale-to-zero is on (`min_machines_running = 0`), so it costs ~nothing idle and
cold-starts on the first request. After this, `git push` to `main` auto-deploys
via the GitHub Action (needs the `FLY_API_TOKEN` repo secret).

## Custom domain (sortiestarter.com, registrar = Hover)

Run from the repo dir (so fly.toml supplies the app), or pass `-a
dcs-mission-starter` explicitly:

```bash
fly certs add sortiestarter.com -a dcs-mission-starter
fly certs add www.sortiestarter.com -a dcs-mission-starter
fly ips list -a dcs-mission-starter          # note the IPv4 (v4) and IPv6 (v6)
fly certs show sortiestarter.com -a dcs-mission-starter   # exact records + status
```

Then in **Hover → your domain → Edit DNS**:

| Type  | Hostname | Value                          |
|-------|----------|--------------------------------|
| A     | `@`      | Fly IPv4 (from `fly ips list`) |
| AAAA  | `@`      | Fly IPv6 (from `fly ips list`) |
| CNAME | `www`    | `dcs-mission-starter.fly.dev`  |

- Delete any default Hover **parking A record** on `@` first.
- TTL: default is fine (drop to 15 min while testing).
- `fly certs show sortiestarter.com` flips to **issued** once DNS resolves; Fly
  auto-provisions Let's Encrypt TLS. `force_https` is already on.

## Sponsor-ads admin (`/admin`)

The sponsor-ads feature is live but the admin is **disabled until you set a
password**:

```bash
fly secrets set ADMIN_PASSWORD='choose-a-strong-one'   # unlocks /admin
```

Then visit `https://sortiestarter.com/admin`, sign in, and add a sponsor by URL
or upload. Without a password the section shows a "not configured" notice and
can't be used.

**Persistence** — sponsors are stored under `SPONSOR_DATA_DIR` (default
`instance/sponsors`, which is ephemeral on Fly). For sponsors to survive
redeploys, mount a volume and point the env at it:

```bash
fly volumes create sponsors --size 1 --region dfw
fly secrets set SPONSOR_DATA_DIR=/data/sponsors
# add to fly.toml, then redeploy:
#   [mounts]
#     source = "sponsors"
#     destination = "/data"
```

## Redeploys

`fly deploy` from the repo root. (Optional: wire a GitHub Action so `git push`
to `main` deploys automatically — ask and I'll add it.)
