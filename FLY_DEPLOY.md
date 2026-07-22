# Deploying to Fly.io

The app is a stateless FastAPI service; `fly.toml` and `Dockerfile` are already
in the repo and verified to build/boot on `python:3.11-slim`.

## One-time setup

```bash
# 1. Install flyctl and log in
brew install flyctl                 # macOS  (or: curl -L https://fly.io/install.sh | sh)
fly auth login

# 2. Create the app from the existing config (do NOT let it re-scaffold)
cd /path/to/DCS-Mission-Starter
fly launch --copy-config --no-deploy
#   - Uses fly.toml as-is, app name "sortiestarter".
#   - If that name is taken globally, pick another and update `app =` in fly.toml.

# 3. Deploy
fly deploy
fly open                            # or: curl https://sortiestarter.fly.dev/api/health  -> {"status":"ok",...}
```

Scale-to-zero is on (`min_machines_running = 0`), so it costs ~nothing idle and
cold-starts on the first request.

## Custom domain (sortiestarter.com, registrar = Hover)

```bash
fly certs add sortiestarter.com
fly certs add www.sortiestarter.com
fly ips list                        # note the shared IPv4 (v4) and IPv6 (v6)
fly certs show sortiestarter.com    # prints the exact A / AAAA records to add
```

Then in **Hover → your domain → Edit DNS**:

| Type  | Hostname | Value                          |
|-------|----------|--------------------------------|
| A     | `@`      | Fly IPv4 (from `fly ips list`) |
| AAAA  | `@`      | Fly IPv6 (from `fly ips list`) |
| CNAME | `www`    | `sortiestarter.fly.dev`        |

- Delete any default Hover **parking A record** on `@` first.
- TTL: default is fine (drop to 15 min while testing).
- `fly certs show sortiestarter.com` flips to **issued** once DNS resolves; Fly
  auto-provisions Let's Encrypt TLS. `force_https` is already on.

## Later — for the sponsor-ads feature

```bash
fly volumes create data --size 1 --region dfw     # small cache/manifest home
fly secrets set ADMIN_PASSWORD='...'              # gates /admin
# then add a [mounts] block to fly.toml pointing at /data and redeploy
```

## Redeploys

`fly deploy` from the repo root. (Optional: wire a GitHub Action so `git push`
to `main` deploys automatically — ask and I'll add it.)
