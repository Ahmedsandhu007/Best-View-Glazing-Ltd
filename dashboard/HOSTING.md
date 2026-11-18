# Putting the dashboard online

On your PC the dashboard works only while the PC is on and only for you (http://127.0.0.1:8787). To open it from anywhere - and later to
give employees a login - it has to run on a computer that is always on. This file is the step-by-step for the two routes that fit, and
the honest answer on Google Apps Script.

**Before any of them:** a password (`DASHBOARD_PASSWORD`), HTTPS, and a GitHub token that is not your everyday one. Without a password
anyone who finds the address could start your stores' jobs.

## What the dashboard needs to work anywhere

| Setting | What | Where it comes from |
|---|---|---|
| `GITHUB_TOKEN` | Lets it read and start the five repositories' GitHub Actions jobs, read and write their files and variables | GitHub -> your profile picture -> Settings -> Developer settings -> Personal access tokens -> *Tokens (classic)* -> Generate new token -> tick **repo** (and **workflow**) -> copy it. One token covers all five repositories because it belongs to your account. (A fine-grained token cannot: it is limited to one owner.) |
| `DASHBOARD_PASSWORD` | The owner password (signs in as admin with an empty username) | You choose a long one |
| `DASHBOARD_USERS` | Named sign-ins: `name:role:password` entries separated by commas; role = view, operate or admin | e.g. `bestview:admin:ChangeMe-2026` |
| `DASHBOARD_SECRET` | Optional: keeps you signed in across restarts when the host forgets files | Any long random text |
| `PORT` or `DASHBOARD_PORT` | The port to listen on | The host usually sets `PORT` itself |

Check after it is up: open the **Help** page - the first table shows the token and the five stores in green when it works.

## Route 1: a small rented server (VPS) - the plan

Roughly 4 to 6 pounds a month at any of the usual providers (Hetzner, DigitalOcean, Vultr, ...). 1 CPU and 1-2 GB of memory is plenty.

1. Rent a server with **Ubuntu 24.04** and note its IP address. In your domain's DNS add an **A record**, for example `dash.yourdomain.com` -> that IP.
2. Log in over SSH and install the pieces:

       sudo apt update && sudo apt install -y python3-venv git caddy

3. Get the code onto the server (the repository is private: use a personal access token in the address, or copy the folder over with WinSCP):

       sudo git clone https://github.com/bestviewglazing/BVG-Site /opt/bvg-site
       cd /opt/bvg-site/dashboard && sudo python3 -m venv .venv && sudo .venv/bin/pip install -r requirements.txt

4. Create the settings file `/opt/bvg-site/dashboard/.env` (then `sudo chmod 600 .env`):

       GITHUB_TOKEN=ghp_your_classic_token
       DASHBOARD_PASSWORD=a-long-password-only-you-know
       DASHBOARD_USERS=bestview:admin:the-clients-own-password
       DASHBOARD_HOST=127.0.0.1
       DASHBOARD_PORT=8787

5. Run it as a service that starts by itself and restarts if it stops. Create `/etc/systemd/system/best-view-glazing-dashboard.service`:

       [Unit]
       Description=Best View Glazing dashboard
       After=network.target

       [Service]
       WorkingDirectory=/opt/bvg-site/dashboard
       ExecStart=/opt/bvg-site/dashboard/.venv/bin/python run.py
       Restart=always
       User=www-data

       [Install]
       WantedBy=multi-user.target

   then:

       sudo mkdir -p /opt/bvg-site/dashboard/data && sudo chown -R www-data /opt/bvg-site/dashboard/data
       sudo systemctl enable --now best-view-glazing-dashboard

6. Put HTTPS in front. Edit `/etc/caddy/Caddyfile` so it contains only:

       dash.yourdomain.com {
           reverse_proxy 127.0.0.1:8787
       }

   then `sudo systemctl reload caddy`. Caddy gets the certificate by itself.
7. Open `https://dash.yourdomain.com`, sign in, open **Help** and check that the GitHub token and all five stores are green.

To update later: `cd /opt/bvg-site/dashboard && sudo git pull && sudo systemctl restart best-view-glazing-dashboard`.

## Route 2: Google Cloud Run (Google's own host, no server to look after)

Cloud Run runs the `Dockerfile` of this folder on demand. A one-person dashboard stays inside its free monthly allowance (check Google's current
pricing), but the account needs billing switched on.

1. In the Google Cloud console create a project and enable billing. Install the Google Cloud CLI and run `gcloud auth login`, then `gcloud config set project YOUR_PROJECT_ID`.
2. In the dashboard folder, deploy (one instance only, so the login cookie and the small database stay in one place):

       gcloud run deploy best-view-glazing-dashboard --source . --region europe-west2 --allow-unauthenticated --max-instances 1 --set-env-vars "DASHBOARD_PASSWORD=a-long-password,GITHUB_TOKEN=ghp_your_classic_token,DASHBOARD_SECRET=some-long-random-text"

   (`--allow-unauthenticated` only means Google does not add its own login in front: the dashboard's own password page still guards everything.
   For the token, Google's Secret Manager with `--set-secrets` is tidier than `--set-env-vars`.)
3. It prints the address (`https://best-view-glazing-dashboard-....run.app`). Open it, sign in, open **Help**.

What to expect: the first page after a quiet spell takes a few seconds (the container starts). Its disk is wiped on every restart, so the **What was
pressed** log and the **Started from here** lists start empty again - everything real (runs, settings, sheets, the committed list files) lives in GitHub
and is not affected.

## Google Apps Script - why not, and what it would take

Apps Script runs JavaScript only, each call is limited to a few minutes, and it has no database or file system. This dashboard is written in Python
(it reads the jobs' logs, evaluates the stores' pricing code, edits list files, builds plans), so it cannot be pasted into Apps Script.

An Apps Script version would have to rebuild every card in JavaScript, the way the eBay orders dashboard is a pair of files you paste and deploy.
It is possible - GitHub's API can be called from Apps Script, Google handles the sign-in, and the settings could live in Script Properties - but it is a
large piece of work and the result is slower and more limited. Only worth it if "Google only, nothing rented" matters more than a server. If you want it,
say which cards matter most and we start with those.

## Security checklist

- A password is set and the address is HTTPS.
- The token is a classic token with `repo` (and `workflow`); revoke it on GitHub if the server is ever lost.
- `.env` is not committed (it is in `.gitignore`) and not readable by others (`chmod 600`).
- Nobody else knows the password until employee logins exist; those come with the VPS step of the plan.
