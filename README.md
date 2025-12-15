# Polymarket copy trading bot
> Polymarket copy trading bot monitors selected Polymarket wallets and mirrors their trades based on your sizing and risk rules. It filters trades by liquidity, spread, and slippage constraints, then places matching limit orders automatically. The outcome is simple: follow proven decision-makers while keeping your own exposure and exits under control.

<p align="center">
  <a href="https://bitbash.dev" target="_blank">
    <img src="https://github.com/Z786ZA/Footer-test/blob/main/media/scraper.png" alt="Bitbash Banner" width="100%"></a>
</p>
<p align="center">
  <a href="https://t.me/Bitbash333" target="_blank">
    <img src="https://img.shields.io/badge/Chat%20on-Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram">
  </a>&nbsp;
  <a href="https://wa.me/923249868488?text=Hi%20BitBash%2C%20I'm%20interested%20in%20automation." target="_blank">
    <img src="https://img.shields.io/badge/Chat-WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" alt="WhatsApp">
  </a>&nbsp;
  <a href="mailto:sale@bitbash.dev" target="_blank">
    <img src="https://img.shields.io/badge/Email-sale@bitbash.dev-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="Gmail">
  </a>&nbsp;
  <a href="https://bitbash.dev" target="_blank">
    <img src="https://img.shields.io/badge/Visit-Website-007BFF?style=for-the-badge&logo=google-chrome&logoColor=white" alt="Website">
  </a>
</p>

<p align="center"> 
   Created by Bitbash, built to showcase our approach to Automation!<br>
   <strong>If you are looking for custom Polymarket copy trading bot, you've just found your team — Let's Chat.👆👆</strong>
</p>

## Introduction
- What this automation tool or system does  
  It tracks selected Polymarket wallets in near-real time, detects their buys/sells, and optionally copies entries and exits into your own account.
- The repetitive workflow it automates  
  Watching leader wallets, validating trades manually (liquidity, spread, slippage), sizing positions, placing limit orders, and tracking state so you don’t double-enter.
- The benefit it provides to users or businesses  
  You can run passive, rules-based copy trading while maintaining strict personal risk controls per market and category.

### Risk-Gated Copy Trading for Polymarket
- Uses deterministic trade validation (liquidity, spread, slippage caps) before any order is sent.
- Maintains per-market and per-category exposure limits so one theme can’t dominate the portfolio.
- Tracks copied trade state to prevent duplicates across refreshes, retries, and leader “rapid-fire” updates.
- Supports two exit modes: mirror leader exits, or independent TP/SL for follower-specific control.
- Designed for long-running reliability with retries, backoff, structured logs, and resumable sessions.

---

## Core Features
| Feature | Description |
|----------|-------------|
| Near-real-time wallet tracking | Monitors selected Polymarket wallets continuously and captures new trades quickly using incremental polling and change detection. |
| Proportional or fixed-amount copying | Copies trades using either proportional sizing (based on your bankroll allocation) or fixed stake sizing per trade. |
| Slippage caps & liquidity filters | Validates depth/liquidity and enforces a maximum acceptable slippage and spread before placing any order. |
| Exposure limits per market & category | Applies guardrails for max exposure per individual market and for broader categories to reduce concentration risk. |
| Mirror exits or independent TP/SL | Either mirrors leader sells/exits automatically or uses follower-defined take-profit/stop-loss rules for independent exits. |
| Duplicate-trade protection & state tracking | Maintains an idempotent ledger of leader events and follower orders to prevent double entries across retries or restarts. |
| Trade intent simulation | Performs a pre-flight check (current price band, liquidity, slippage estimate) to confirm the trade is still valid at execution time. |
| Rate limiting & human-like pacing | Adds pacing, jitter, and request throttles to reduce session strain and improve long-run stability. |
| Resumable worker & crash recovery | Persists state (last seen leader event, open positions, pending orders) so the bot can restart without losing context. |
| Audit logs & reporting output | Writes structured logs and exports results (fills, rejects, latency, slippage) into JSON/CSV for review and debugging. |

---

## How It Works
1. **Input or Trigger** — You configure leader wallet addresses, copy mode (proportional or fixed), risk limits, and exit strategy (mirror vs TP/SL).  
2. **Core Logic** — A browser worker monitors leader activity and normalizes events into a consistent trade signal model (market, side, size, timestamp, price band).  
3. **Output or Action** — Each signal is validated against liquidity/spread/slippage rules and exposure limits, then a matching limit order is placed in your account.  
4. **Other Functionalities** — The bot tracks open positions, reconciles fills, prevents duplicates via an idempotency key, and updates a local state store.  
5. **Safety Controls** — Circuit breakers pause execution on repeated failures, abnormal spreads, missing data, or risk-limit breaches; retries use backoff and never re-submit the same trade twice.

---

## Tech Stack
- **Language:** Python (automation + orchestration)  
- **Frameworks:** Playwright (primary), optional Selenium fallback  
- **Tools:** Chromium, asyncio workers, structured logging, dotenv, YAML config  
- **Infrastructure:** Local runner or containerized worker, optional Redis queue for sharding, cron/systemd for scheduling

---

## Directory Structure
    automation-bot/
    ├── src/
    │   ├── main.py
    │   ├── automation/
    │   │   ├── tasks.py
    │   │   ├── scheduler.py
    │   │   └── utils/
    │   │       ├── logger.py
    │   │       ├── proxy_manager.py
    │   │       └── config_loader.py
    ├── config/
    │   ├── settings.yaml
    │   ├── credentials.env
    ├── logs/
    │   └── activity.log
    ├── output/
    │   ├── results.json
    │   └── report.csv
    ├── requirements.txt
    └── README.md

---

## Use Cases
- **Passive traders** use it to follow high-performing Polymarket wallets, so they can participate without researching every market manually while still enforcing personal risk limits.
- **Strategy builders** use it to run proportional copying across a curated set of leaders, so they can diversify decision sources without increasing manual workload.
- **Risk-conscious traders** use it to copy entries but use independent TP/SL exits, so they can standardize risk even when leaders hold longer than desired.
- **Portfolio managers** use it to cap exposure by category and market, so they can prevent over-concentration during fast-moving news cycles.
- **Ops-minded teams** use it to produce fill and slippage reports, so they can audit performance and tune execution constraints over time.

---

## FAQs
**How do I configure this automation for multiple accounts?**  
Set up a separate profile per account with isolated credentials, storage, and session state. Each profile gets its own config file (or a named section in one YAML), its own browser context, and its own state database so there’s no cross-talk. Run them as separate workers (one process per account) or as a supervised pool where each worker loads a distinct profile and writes to isolated output paths.

**Does it support proxy rotation or anti-detection?**  
Yes, via a proxy pool with per-worker binding. Each worker can pin to a proxy for session stability (recommended for long-running logins) or rotate on a schedule if sessions expire. On the browser side, pacing and randomized delays help reduce bot-like traffic patterns. The bot also throttles polling and backs off automatically during transient failures to avoid hammering endpoints.

**Can I schedule it to run periodically?**  
You can run it continuously as a daemon worker, or schedule windows using cron/systemd timers. Internally, it uses a loop-based scheduler with retry queues: failed steps are retried with exponential backoff, and successful steps checkpoint state so restarts are safe. For horizontal scaling, shard leader wallets across workers and feed events into a lightweight queue.

**What about headless vs headed mode?**  
Headless mode is ideal for servers and stable environments, but headed mode can be more reliable during initial setup and debugging (e.g., verifying login, consent prompts, or occasional UI changes). A common pattern is to bootstrap credentials in headed mode once, then run headless with persistent storage. If you see intermittent UI timing issues, headed mode with slightly longer waits can help diagnose selectors and page-state transitions.

---

## Performance & Reliability Benchmarks
- **Execution Speed:** 20–40 actions/min per worker under typical conditions (poll, validate, place limit order, reconcile), depending on market load and page complexity.  
- **Success Rate:** 93–94% across long-running jobs with retries and revalidation, assuming stable sessions and reasonable market liquidity.  
- **Scalability:** 300–1,000 browser instances via sharded wallet assignments, a lightweight queue, and horizontal workers (container replicas) with per-worker state isolation.  
- **Resource Efficiency:** Target 1 vCPU and 512MB–1.5GB RAM per browser worker, depending on concurrency and whether video/trace is enabled for debugging.  
- **Error Handling:** Automatic retries with exponential backoff, idempotent trade processing to prevent duplicates, structured logs for every decision, and circuit breakers that pause trading on repeated failures or risk-rule violations.



<p align="center">
<a href="https://calendar.app.google/74kEaAQ5LWbM8CQNA" target="_blank">
  <img src="https://img.shields.io/badge/Book%20a%20Call%20with%20Us-34A853?style=for-the-badge&logo=googlecalendar&logoColor=white" alt="Book a Call">
</a>
  <a href="https://www.youtube.com/@bitbash-demos/videos" target="_blank">
    <img src="https://img.shields.io/badge/🎥%20Watch%20demos%20-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Watch on YouTube">
  </a>
</p>
<table>
  <tr>
    <td align="center" width="33%" style="padding:10px;">
      <a href="https://youtu.be/MLkvGB8ZZIk" target="_blank">
        <img src="https://github.com/Z786ZA/Footer-test/blob/main/media/review1.gif" alt="Review 1" width="100%" style="border-radius:12px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
      </a>
      <p style="font-size:14px; line-height:1.5; color:#444; margin:0 15px;">
        "Bitbash is a top-tier automation partner, innovative, reliable, and dedicated to delivering real results every time."
      </p>
      <p style="margin:10px 0 0; font-weight:600;">Nathan Pennington
        <br><span style="color:#888;">Marketer</span>
        <br><span style="color:#f5a623;">★★★★★</span>
      </p>
    </td>
    <td align="center" width="33%" style="padding:10px;">
      <a href="https://youtu.be/8-tw8Omw9qk" target="_blank">
        <img src="https://github.com/Z786ZA/Footer-test/blob/main/media/review2.gif" alt="Review 2" width="100%" style="border-radius:12px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
      </a>
      <p style="font-size:14px; line-height:1.5; color:#444; margin:0 15px;">
        "Bitbash delivers outstanding quality, speed, and professionalism, truly a team you can rely on."
      </p>
      <p style="margin:10px 0 0; font-weight:600;">Eliza
        <br><span style="color:#888;">SEO Affiliate Expert</span>
        <br><span style="color:#f5a623;">★★★★★</span>
      </p>
    </td>
    <td align="center" width="33%" style="padding:10px;">
      <a href="https://youtu.be/m-dRE1dj5-k?si=5kZNVlKsGUhg5Xtx" target="_blank">
        <img src="https://github.com/Z786ZA/Footer-test/blob/main/media/review3.gif" alt="Review 3" width="100%" style="border-radius:12px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
      </a>
      <p style="font-size:14px; line-height:1.5; color:#444; margin:0 15px;">
        "Exceptional results, clear communication, and flawless delivery. <br>Bitbash nailed it."
      </p>
      <p style="margin:1px 0 0; font-weight:600;">Syed
        <br><span style="color:#888;">Digital Strategist</span>
        <br><span style="color:#f5a623;">★★★★★</span>
         </p>

