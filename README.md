# UGSI McElroy Shop

Parts inventory and fleet management for McElroy butt-fusion machines.
Built for the Underground Solutions shop (Azuria Water Solutions).

## What This Does

- **Parts Inventory**: 6,299 McElroy parts with stock tracking, barcode scanning, and reorder alerts
- **Fleet Management**: 36 machines (618/900/1200) with job assignments and status tracking
- **Scan-to-Shelf**: Shop manager scans a part → app shows what machines it fits, stock level, and location
- **Field Support**: Tech calls in with machine QR → shop manager sees all compatible parts in stock
- **Reports**: Interactive reports with CSV download, email, share, and copy
- **MCP Integration**: AI agents can query inventory via Model Context Protocol

## Architecture

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  iPhone/Web  │────▶│  Caddy Proxy  │────▶│  InvenTree   │
│  (shop app)  │     │  :8080        │     │  (Django)    │
└──────────────┘     └───────────────┘     └──────────────┘
                            │                      │
                     ┌──────┘               ┌──────┘
                     ▼                      ▼
              ┌─────────────┐        ┌─────────────┐
              │  shop/      │        │  PostgreSQL  │
              │  index.html │        │  + Redis     │
              └─────────────┘        └─────────────┘

┌──────────────┐     ┌───────────────┐
│  Claude Code │────▶│  MCP Server   │──── InvenTree API
│  (AI agent)  │     │  (stdio)      │
└──────────────┘     └───────────────┘
```

## Quick Start

### Shop Laptop (Full System)

```bash
# Prerequisites: Docker Desktop
docker-compose up -d

# Open in browser
open http://localhost:8080/shop/

# iPhone: connect to shop WiFi, open http://<laptop-ip>:8080/shop/
# Tap Share → Add to Home Screen
```

### Standalone (View Only)

Open `dist/UGSI_McElroy_Shop.html` in any browser. All 6,299 parts are embedded — no server needed.

### MCP Server (AI Integration)

```bash
# Register with Claude Code
claude mcp add ugsi-shop python3 -m mcp_server.server

# Now Claude can query:
# "What parts do I need for UGSI-618-001?"
# "What's low stock right now?"
# "Show me all 900s in the field"
```

## Project Structure

```
mcelroy-inventory/
├── shop/                   # Front-end (single HTML file)
│   ├── index.html          # Main app — PWA, local-first, Azuria branded
│   └── manifest.json       # PWA manifest for Add to Home Screen
├── mcp_server/             # MCP server for AI agent integration
│   ├── server.py           # MCP protocol handler + tool definitions
│   ├── inventree_client.py # InvenTree API client (swappable backend)
│   └── config.py           # Configuration management
├── docker-compose.yml      # InvenTree + Postgres + Redis + Caddy
├── Caddyfile               # Reverse proxy config
├── parts_data.py           # Curated parts catalog (100 key parts)
├── load_stock.py           # Stock data loader
├── import_to_inventree.py  # Full catalog importer
└── test_shop_workflow.py   # 25 Playwright E2E tests
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `lookup_machine` | Machine ID → compatible parts + stock levels |
| `lookup_part` | Search parts by name, SKU, or keyword |
| `check_stock` | Stock levels for a part or overall status |
| `adjust_stock` | Add/remove stock (requires write mode) |
| `fleet_status` | List machines by status/family/job |
| `low_stock_report` | Parts below reorder point |
| `inventory_snapshot` | Full inventory summary |
| `system_health` | Connection and config status |
| `get_config` / `set_config` | Read/write server configuration |
| `import_csv` | Import data from legacy systems |

## Configuration

Settings are managed via:
1. **Control panel** in the shop app (Settings tab)
2. **Environment variables** (prefixed `UGSI_`)
3. **Config file** at `config/settings.json`

Key settings:
- `UGSI_DEV_MODE=true` — Enable debug logging and dev tools
- `UGSI_ENABLE_WRITES=true` — Allow stock modifications via MCP
- `UGSI_INVENTREE_URL` — InvenTree server URL
- `INVENTREE_PASSWORD` — InvenTree password (env only, never stored)

## Integrations (Planned)

The system is designed to plug into existing infrastructure:

- **SharePoint/OneDrive**: Auto-upload reports to shared folders
- **Email/SMTP**: Automated low-stock alerts to purchasing
- **CSV Import**: Watch folder for exports from legacy inventory systems
- **ERP Sync**: Push stock changes to existing accounting/ERP

Each integration has an enable flag and configuration section in the control panel.

## For IT

- All secrets are in environment variables, never in code or config files
- Docker Compose handles the full stack — one command to deploy
- InvenTree is open source (inventree.org) — no vendor lock-in
- MCP server uses stdio protocol — no network ports to manage
- The shop app is a single HTML file with no build step
- All 25 E2E tests pass (Playwright)

## License

Internal tool for Underground Solutions / Azuria Water Solutions.
