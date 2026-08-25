# RideWise — Docker + systemd ("both together") deployment

This is the setup you asked about: **Docker guarantees the environment, systemd
keeps it running.** It's a small step up from your current systemd-only
deployment and it closes the reproducibility gap that caused most of the
debugging pain (the `os`/`httpx2` requirements bug, unpinned pandas/numpy,
scikit-learn pickle drift).

## The division of labour

| Layer | Tool | Answers |
|-------|------|---------|
| **What runs** | Docker (`Dockerfile`, `docker-compose.yml`) | "The exact same environment, every time" |
| **That it keeps running** | systemd (`ridewise.service`) | "Start on boot, restart on failure, one control point" |
| **Who the internet talks to** | Nginx (`nginx/ridewise.conf`) | "Only port 80/443 is public; route / to the UI, /api to the API" |

Compared to your original setup, the **only conceptual change** is that
systemd now supervises a *Docker Compose stack* instead of a bare `uvicorn`
process. Everything else you already know still applies.

## Files

```
Dockerfile               # packages the app: pinned Python + deps + models
docker-compose.yml       # runs API (8000) + UI (8501) together, loopback-only
.dockerignore            # keeps the image small and secrets out
systemd/ridewise.service # supervises the whole stack; survives reboots
nginx/ridewise.conf      # reverse proxy; fixes the root-serves-API routing bug
```

## One-time server setup (Amazon Linux 2023)

```bash
# Install Docker + the compose plugin (the plugin IS available via dnf on AL2023)
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user          # log out/in to take effect

# Compose plugin
sudo mkdir -p /usr/libexec/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
     -o /usr/libexec/docker/cli-plugins/docker-compose
sudo chmod +x /usr/libexec/docker/cli-plugins/docker-compose
docker compose version                     # verify
```

## Deploy

```bash
# 1. Put the code + these files on the server
cd /home/ec2-user/app
git clone <your-repo> .    # or git pull

# 2. Install the systemd unit that supervises the stack
sudo cp systemd/ridewise.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ridewise             # start on boot
sudo systemctl start ridewise              # builds images + starts both containers

# 3. Install the Nginx config
sudo cp nginx/ridewise.conf /etc/nginx/conf.d/
sudo nginx -t                              # validate syntax
sudo systemctl restart nginx
```

That's it. `systemctl start ridewise` runs `docker compose up -d --build`, which
builds the image and launches both containers. Nginx routes the public traffic.

## Daily operations — same muscle memory as before

```bash
# Is it up? (systemd view)
sudo systemctl status ridewise

# App logs (both containers)
docker compose logs -f            # or: docker logs -f ridewise-api

# Restart everything
sudo systemctl restart ridewise

# Deploy a new version
git pull && sudo systemctl reload ridewise    # rebuilds + recreates changed containers

# What's listening?
ss -tlnp | grep -E '8000|8501|80'
```

Your three-command triage from the Journey Report still works —
`systemctl status`, `journalctl -u ridewise`, `ss` — plus `docker compose logs`
for inside-the-container detail.

## Why this fixes the environment problems

- **`os` / `httpx2` / version drift** — caught once at `docker build`, then frozen
  into the image. The server never runs a fresh `pip install`, so a clean deploy
  can't fail on dependencies again.
- **scikit-learn pickle compatibility** — the version that saved the model and the
  version that loads it are the same pinned version, baked into the image.
- **"works on my machine"** — the image runs identically on your laptop and EC2.

## What this does NOT change

- You still choose **one** runtime story. This IS that story now — retire the
  bare-uvicorn systemd unit so there's no ambiguity.
- Nginx, HTTPS, security groups, SSH hardening — all still apply exactly as on the
  go-live checklist. Docker packages the app; it doesn't secure the front door.

## Rolling back

```bash
git checkout <last-good-tag>
sudo systemctl reload ridewise    # rebuilds from the known-good commit
```

Because the image is rebuilt from a pinned commit + pinned requirements, the
rollback lands on a byte-for-byte known-good environment.
