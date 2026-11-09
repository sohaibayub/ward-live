# Deploying WARD Live

The server is one Python process. Either route below gives a public HTTPS address in a few minutes. For the stand itself, run it on the laptop with `uvicorn app:app`.

## Vercel (free, no card)

Hugging Face Spaces no longer hosts Docker apps for free (since July 2026), so Vercel is the free route.

1. Put the ward-live folder in a GitHub repository.
2. Sign in at vercel.com with GitHub, choose Add New Project, pick the repository, leave the settings as detected (the vercel.json and api/index.py in the folder tell Vercel what to run) and click Deploy.
3. After about a minute the app is at https://<project-name>.vercel.app. Every push to the repository redeploys.
4. Put that address in extension/popup.js as DEFAULT and in the store listing.

Vercel functions cannot write files, so the contributor study page (/study) does not keep records there; run the study from the laptop. Audits, reports and the task CSV all work. The Hobby plan is for non-commercial use.

## Fly.io (about 2 to 3 euro a month, card required)

1. Install flyctl and run `fly auth signup` (or `fly auth login`).
2. In this folder run `fly launch --copy-config --no-deploy`, accept the app name or change it in fly.toml, then `fly deploy`.
3. The app is at https://ward-live.fly.dev (or the name you chose). The machine stays on, so there is no sleep.
4. To keep the study log across deploys: `fly volumes create data --size 1 --region ams` and add to fly.toml

       [mounts]
         source = "data"
         destination = "/app/data"

## Your own domain later

Both hosts let you attach a custom domain and issue the certificate for you. If a university or other name becomes available, add it there and update the extension default.
