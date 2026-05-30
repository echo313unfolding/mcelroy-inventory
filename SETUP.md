# McElroy Parts Inventory - Setup Guide
## Underground Solutions (Azuria/Aegion)

### What This Is
A parts inventory system for tracking McElroy fusion machine parts across your fleet:
- **~20x 618s** (TracStar, Rolling, Pit Bull — standard + i-series)
- **~12x 900s** (TracStar — standard + i-series)
- **~4x 1200s** (TracStar + MegaMc — standard + i-series)

Uses [InvenTree](https://inventree.org) (open source, MIT license) running in Docker on the shop laptop. Phones connect over Wi-Fi for barcode scanning.

---

### Prerequisites
- Shop laptop with Docker Desktop installed
- Windows: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- All phones on same Wi-Fi as laptop

### Step 1: Install Docker
Download and install Docker Desktop. Restart the laptop after install.

### Step 2: Start the System
Open a terminal (PowerShell on Windows, Terminal on Mac) and run:

```bash
cd mcelroy-inventory
docker compose up -d
```

First run downloads images (~2 GB). Takes 5-10 minutes on shop internet.

Wait 2 minutes for the database to initialize, then:

```bash
# Create the database tables
docker compose run --rm inventree-server invoke update

# Create the admin account
docker compose run --rm inventree-server invoke superuser
```

### Step 3: Log In
Open a browser and go to: **http://localhost:8080**

Login:
- Username: `shopmanager`
- Password: `ugsi2026!`

(Change the password in `.env` BEFORE first run, or change it in the web UI after.)

### Step 4: Load Parts Data
On the machine running Docker:

```bash
pip install requests
python3 import_to_inventree.py
```

This loads:
- 30+ part categories (Jaw Inserts, Facer Blades, Heaters, Hydraulics, etc.)
- 90+ parts with McElroy part numbers where known
- 9 stock locations (Shop, Parts Room, Field, In Service, etc.)
- 36 machine locations (one per machine in your fleet)
- 7 custom parameter templates (Pipe Size, Machine Family, Force Rating, etc.)

### Step 5: Phone Access
Find the laptop's IP address:
- Windows: `ipconfig` → look for IPv4 Address (e.g., 192.168.1.100)
- Mac: System Preferences → Network

On each phone's browser, go to: **http://[LAPTOP_IP]:8080**

For barcode scanning, use the **InvenTree app**:
- iOS: [InvenTree on App Store](https://apps.apple.com/app/inventree/id1581731101)
- Android: [InvenTree on Play Store](https://play.google.com/store/apps/details?id=inventree.inventree)

In the app settings, enter:
- Server: `http://[LAPTOP_IP]:8080`
- Username/Password: same as web login

### Step 6: Add Real Data
After the base import, you'll want to:

1. **Machine serial numbers**: Go to Stock → Fleet → each machine → edit description to add the real McElroy serial number
2. **Stock counts**: For each part, add the actual quantity you have on hand
3. **Part numbers**: Look up exact McElroy part numbers at [McElroy Parts Finder](https://fusion.mcelroy.com/parts/exec) and update the IPN field
4. **Pricing**: Add supplier info and pricing from McElroy or your distributor
5. **Photos**: Take photos of parts and upload to each part record

---

### Daily Use

**Issue parts to a machine:**
1. Scan the part barcode (or find it in the app)
2. Transfer stock from "Shop - Parts Room" to the machine location (e.g., "UGSI-618-003")
3. The system tracks what's installed on which machine

**Receive parts:**
1. Scan incoming parts
2. Add stock to "Shop - Parts Room"
3. System updates quantities and checks against reorder points

**Check what's low:**
- Dashboard shows parts below minimum stock level
- Set up email alerts for reorder notifications

**Track serialized assets:**
- DataLoggers, facers, heaters, insert sets, cylinders are tracked by serial number
- Transfer history shows which machine each asset has been on

---

### Backup
Back up the database regularly:

```bash
docker compose exec inventree-db pg_dump -U inventree inventree > backup_$(date +%Y%m%d).sql
```

### Stop / Restart

```bash
# Stop
docker compose down

# Restart
docker compose up -d
```

Data persists in Docker volumes between restarts.

---

### Parts Data Source
Parts data built from:
- McElroy TracStar 618/412/28 Operator's Manual (T1810001 Rev G)
- McElroy No.412 & No.618 Operator's Manual (1821901 Rev B)
- McElroy Fusion Catalog & Reference Guide
- McElroy Parts Finder (fusion.mcelroy.com)
- mcelroyparts.com (MIMECO distributor)

Part numbers are best-effort from available sources. Verify against your machine's parts breakdown before ordering.
