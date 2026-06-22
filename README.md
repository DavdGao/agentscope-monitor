# agentscope-monitor

Private storage + automation repo that monitors
[agentscope-ai/agentscope](https://github.com/agentscope-ai/agentscope) and
sends Dingtalk notifications.

## What it does

1. **Real-time push** — every issue / PR / discussion / comment / push
   event on the monitored repo triggers a Dingtalk message.
2. **Persistent log** — each event is stored here at
   `data/YYYY-MM-DD/<event_id>.json`. No git push conflicts: writes go
   through the GitHub Contents API.
3. **Daily digest** — at 10:00 Beijing time every day, yesterday's events
   are aggregated into a Markdown report (new issues/PRs/discussions,
   comment activity, PRs with new commits to re-review) and pushed to the
   same Dingtalk group.

## Architecture

```
agentscope-ai/agentscope  ──(event)──►  github-monitor.yml
                                            │ checkout this repo
                                            │ run scripts/notify.py
                                            ├─► PUT data/...json (Contents API)
                                            └─► Dingtalk markdown

this repo  ──(cron 02:00 UTC)──►  daily-summary.yml
                                       └─► run scripts/summary.py
                                              ├─ read data/<yesterday>/
                                              └─► Dingtalk digest
```

## Deploy — one-time setup

### 1. Create a Dingtalk bot

In the target Dingtalk group → 群设置 → 智能群助手 → 添加机器人 → 自定义。

- **安全设置**：勾选 **自定义关键词**, value = `AgentScope`
  (every message sent by this monitor automatically includes this
  keyword; without it Dingtalk will silently drop the message).
- (Optional) Also enable **加签** for extra security — copy the secret
  starting with `SEC...`.
- Copy the webhook URL.

### 2. Create the private storage repo (push code at the same time)

```bash
cd /Users/david/Documents/Python/monitor
git init
git add .
git commit -m "Initial: agentscope github monitor"
gh repo create DavdGao/agentscope-monitor --private --source=. --push
```

`gh repo create --source=. --push` creates the remote private repo,
sets `origin`, and pushes `main` in one shot. Doing `git init` first
avoids the *"current directory is not a git repository"* prompt.

> Private repos can run GitHub Actions. Personal-account private repos
> have 2 000 free Linux-runner minutes per month, which is far more than
> this monitor needs.

### 3. Create a Fine-grained PAT

The repo now exists, so the PAT can target it by name.

Go to: **GitHub → avatar → Settings → Developer settings (left sidebar,
at the very bottom) → Personal access tokens → Fine-grained tokens →
Generate new token**.
Direct link: <https://github.com/settings/personal-access-tokens>.

Fill in:

| Field | Value |
|---|---|
| Token name | `agentscope-monitor-storage` |
| Expiration | 1 year (set a calendar reminder) |
| Resource owner | your account (e.g. `DavdGao`) |
| Repository access | **Only select repositories** → pick `DavdGao/agentscope-monitor` |
| Permissions → Repository permissions → **Contents** | **Read and write** (leave everything else as *No access*) |

Click **Generate token** and copy the value immediately (starts with
`github_pat_...`) — you can never view it again after leaving the page.

### 4. Configure secrets on this repo (`DavdGao/agentscope-monitor`)

For the daily digest workflow:

| Secret | Required | Value |
|---|---|---|
| `DINGTALK_WEBHOOK` | yes | bot webhook URL |
| `DINGTALK_SECRET`  | optional | bot signing secret (only if you enabled 加签) |
| `DING_OWNER_MAP`   | optional | JSON `{"nickname":"mobile",...}` — only needed if you want the 10:00 digest to @ on-call people. See [@ rotation](#-mention-people-in-real-time-messages). |

```bash
gh secret set DINGTALK_WEBHOOK   -R DavdGao/agentscope-monitor
gh secret set DINGTALK_SECRET    -R DavdGao/agentscope-monitor   # if used
gh secret set DING_OWNER_MAP     -R DavdGao/agentscope-monitor   # if used
```

### 5. Configure secrets on the monitored repo (`agentscope-ai/agentscope`)

For the real-time notification workflow:

| Secret | Required | Value |
|---|---|---|
| `STORAGE_REPO_TOKEN` | yes | the Fine-grained PAT from step 2 |
| `DINGTALK_WEBHOOK`   | yes | bot webhook URL |
| `DINGTALK_SECRET`    | optional | bot signing secret |
| `DING_OWNER_MAP`     | optional | same JSON as above; needed if you ever want realtime events to @ someone |

```bash
gh secret set STORAGE_REPO_TOKEN -R agentscope-ai/agentscope
gh secret set DINGTALK_WEBHOOK   -R agentscope-ai/agentscope
gh secret set DINGTALK_SECRET    -R agentscope-ai/agentscope     # if used
gh secret set DING_OWNER_MAP     -R agentscope-ai/agentscope     # if used
```

### 6. Add the monitor workflow to the monitored repo

Copy [`templates/github-monitor.yml`](templates/github-monitor.yml) to
`agentscope-ai/agentscope/.github/workflows/github-monitor.yml` and
open a PR.

> If your storage repo is **not** `DavdGao/agentscope-monitor`, edit
> the `repository:` and `STORAGE_REPO:` values inside the template
> before committing.

### 7. Verify

- On this repo: Actions → **Daily Summary** → *Run workflow* (you can
  use `dry_run=1` to print the report without sending).
- On the monitored repo: open a throwaway issue and confirm a Dingtalk
  message arrives + a new file appears under `data/<today>/` here.

## Customization

### Choose which events to watch

`templates/github-monitor.yml` — edit the `on:` block.
`scripts/config.py` — `WATCHED_EVENTS` filters again at the script level.

### @-mention people

Mobile numbers are PII and **never live in git**. They are stored in a
single GitHub Secret called `DING_OWNER_MAP` (a JSON object), and the
nickname-based rotation tables in `scripts/config.py` reference those
nicknames.

#### Step 1 — set `DING_OWNER_MAP` secret

```bash
echo '{"dawei":"13xxxxxxxxx","chenguan":"13yyyyyyyyy"}' | \
    gh secret set DING_OWNER_MAP -R DavdGao/agentscope-monitor

# repeat for the monitored repo if you want realtime @ too:
echo '{"dawei":"13xxxxxxxxx","chenguan":"13yyyyyyyyy"}' | \
    gh secret set DING_OWNER_MAP -R agentscope-ai/agentscope
```

The keys (`dawei`, `chenguan`, …) are arbitrary nicknames you reuse
below. To add/remove a person, re-run `gh secret set` with the full
updated JSON (secrets are write-only — you can't merge values).

#### Step 2 — weekly on-call rotation (10:00 digest only)

Edit `scripts/config.py`:

```python
WEEKDAY_ON_CALL = {
    0: ["dawei", "chenguan"],   # 周一
    1: ["someone"],             # 周二
    2: ["dawei", "chenguan"],   # 周三
    3: ["someone"],             # 周四
    4: ["dawei", "chenguan"],   # 周五
    5: ["someone"],             # 周六
    6: [],                      # 周日: no @
}
```

Commit and push — no PII, just nicknames.

#### Step 3 (optional) — real-time @ for specific labels / paths

`LABEL_OWNER_MAP`, `MODULE_OWNER_MAP` in `scripts/config.py` work the
same way (nicknames only). For a smarter router, replace
`resolve_mentions` in `scripts/mentions.py` with a call to your LLM
and return a list of nicknames (or directly mobiles).

#### Notes / caveats

- Only **mobile numbers** trigger a real Dingtalk push notification in
  a self-built robot group. atUserIds, 阿里钉号, email prefixes only
  render the @ text without notifying.
- Nicknames in `WEEKDAY_ON_CALL` that are missing from `DING_OWNER_MAP`
  are silently dropped (so an empty / unset secret simply means "no @").

### Change the digest time

`.github/workflows/daily-summary.yml` — edit the cron. Remember it is
UTC: 10:00 Asia/Shanghai = `0 2 * * *`.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m tests.test_pipeline                # parser + summary smoke test
DRY_RUN=1 REPORT_DAY=2026-06-21 python -m scripts.summary
```

## Layout

```
scripts/
  config.py        constants, repo names, timezone, mention tables
  dingtalk.py      webhook client (keyword + optional sign)
  storage.py       Contents-API based event writer / reader
  mentions.py      @-rule resolver (LLM hook point)
  parser.py        webhook payload → normalized event dict
  notify.py        entry point invoked by the monitored repo
  summary.py       entry point invoked by the daily cron
.github/workflows/
  daily-summary.yml
templates/
  github-monitor.yml   ← copy to monitored repo
data/
  YYYY-MM-DD/<event_id>.json
tests/
  test_pipeline.py
```
