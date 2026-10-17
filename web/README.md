# CFB Analytics Hub — website

The standalone site that replaces the Streamlit app. It's a Next.js site that
builds to plain static pages, so there is no server to run or pay for.

## Your weekly routine

Same as before, plus one step:

```
python update_data.py
python score_model.py
python export_web_data.py      <- new: writes web/public/data/
```

Then commit and push in GitHub Desktop. Vercel sees the push and rebuilds the
site in about a minute.

`export_web_data.py` does all the math the Streamlit pages used to do and saves
the results as JSON. The website only displays them.

## One-time setup on Vercel

1. Go to vercel.com and sign in with GitHub.
2. **Add New → Project**, pick the `College-Football-Site` repo, click **Import**.
3. Set **Root Directory** to `web`. Leave everything else on the defaults
   (Framework: Next.js, Build: `next build`).
4. Click **Deploy**. You'll get a `*.vercel.app` link. Add your own domain
   under **Settings → Domains** if you want one.

Every push to `main` redeploys automatically.

## Running it on your computer

### One-time setup
1. Install **Node.js LTS** (version 20 or newer) from https://nodejs.org with the default options.
   Close any open Command Prompt / PowerShell / VS Code windows afterwards; only new windows can find it.
2. Make sure the data exists: `web\public\data\meta.json` should be there. If not, run
   `python export_web_data.py` from the main project folder (needs pandas and numpy, Python 3.8+).
3. Pause OneDrive syncing (OneDrive icon → gear → Pause syncing) before the first install.
   `npm install` writes ~30,000 small files into `web\node_modules`; OneDrive locking them mid-install
   is the most common cause of `EPERM` / `EBUSY` errors. Git already ignores that folder.

### Start it
Double-click **`web\start-site.bat`**. It checks Node, installs packages on the first run, starts the
site and opens http://localhost:3000. Keep the black window open while you browse; Ctrl+C stops it.

Or by hand, in Command Prompt (not PowerShell, see below):
```
cd "%USERPROFILE%\Desktop\College Football Site\web"
npm install
npm run dev
```
The quotes matter because the folder name has spaces.

### After a data update
Run `python export_web_data.py`, then refresh the browser. No restart needed.

### If something goes wrong
| What you see | Fix |
|---|---|
| `'node' is not recognized` / `'npm' is not recognized` | Node isn't installed, or the window was open before you installed it. Open a new window. |
| PowerShell: `npm.ps1 cannot be loaded because running scripts is disabled` | Use Command Prompt (or start-site.bat), or run `npm.cmd install` / `npm.cmd run dev` instead. |
| `EPERM`, `EBUSY` or `operation not permitted` during install | OneDrive or antivirus has a file locked. Pause OneDrive, delete `web\node_modules`, run `npm install` again. |
| Windows Firewall pops up for Node.js | Allow on private networks (or Cancel; localhost still works). |
| `Port 3000 is in use` | Next picks 3001 automatically; use the address it prints. |
| The first click on a page is slow | Normal in dev mode: each page compiles the first time you open it. |
| Fonts look plain / logos are colored circles | You're offline; fonts and logos load from the internet. |
| `Unsupported engine` or `next` errors about Node | Your Node is older than 20. Install the current LTS. |

### Preview the production version
`npm run build` makes the finished static site in `web\out` (same thing Vercel serves).
To view it: `cd out` then `python -m http.server 3000`, and open http://localhost:3000.

## Where things live

| Page | File |
|---|---|
| This Week (home) | `app/page.tsx` |
| Picks (Sharp Bets) | `components/PicksView.tsx`, `components/PickCard.tsx` |
| Matchups / game pages (Weekly Preview) | `app/matchups/`, `app/games/[id]/page.tsx` |
| Team pages (Roster Analysis, transfers, ATS) | `app/teams/[slug]/page.tsx`, `components/TeamView.tsx` |
| Compare teams (Team Comparison) | `components/CompareView.tsx` |
| Quarterbacks | `components/QbView.tsx` |
| Transfer Portal | `components/PortalView.tsx` |
| ATS Results (Betting Results) | `components/BettingView.tsx` |
| Model Record | `app/model/page.tsx` |
| Colors, fonts | `app/globals.css` |

## Each new season

Update the constants at the top of `export_web_data.py` (`SEASON`,
`PRIOR_SEASON` and the roster / recruit / transfer file names).
