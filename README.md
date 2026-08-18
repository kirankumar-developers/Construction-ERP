# Construction Site Management ERP Web Application

A complete, production-grade **Construction Site / Project Management ERP Web Application** built using **Python Flask**, **MongoDB**, **Bootstrap 5**, **Chart.js**, and **OpenStreetMap (Leaflet.js)**. 

This platform supports 10 distinct user roles, complete site location mapping, detailed tasks and subtasks, BOQ items, budget variance analysis, Daily Progress Reports (DPR), inventory ledger transactions, procurement indents, RFQ vendor bidding, and client billing.

---

## 1. Core Modules

* **Company Management**: Settings, address, multi-project and multi-site support, user directories.
* **Project Management**: Project codes, start/end dates, priorities, budget targets, progress percentage, milestones, delays, issues, activity.
* **Site Management**: GPS site location markers with OpenStreetMap + Leaflet.js coordination.
* **BOQ Estimates**: Item descriptions, quantity, rate calculations, budget variance trackers.
* **Budget Tracking**: Category-wise cost controls (Material, Labour, Equipment, Subcontractor, Transport, Other).
* **Task & Subtask System**: Task assignment, comments, file attachments, and completion sliders.
* **Daily Progress Reports (DPR)**: Site Engineer submissions, labour counts, material consumption, equipment hours, weather details, and PM reviews.
* **Inventory Ledger**: Stock in, stock out, transfers, returns, low-stock warnings.
* **Procurement Engine**: Indent -> PM Review -> RFQ -> Vendor Quotes -> Bidding Comparisons -> PO -> GRN -> Supplier Bill -> Payments.
* **Vendor & Subcontractor Profiles**: Supplier catalogs, work orders, payment logs, and outstanding balances.
* **Labour force Management**: Daily shifts attendance sheets, automatic wage computations.
* **Employee Geotagged Attendance**: Browser geolocation tracking check-in and check-out logs.
* **Equipment Ledger**: Machinery rental tracking, usage histories, maintenance cost logs.
* **Reports Dashboard**: Date-filtered Chart.js graphs for project progress, category expenses, material stocks, and cash flow profitability.

---

## 2. Default Seed Accounts

Run the database seeder to populate these sample accounts:

| Role | Email Login | Password |
| :--- | :--- | :--- |
| **Super Admin** | `superadmin@onsiteerp.com` | `admin123` |
| **Admin** | `admin@onsiteerp.com` | `admin123` |
| **Project Manager** | `pm@onsiteerp.com` | `admin123` |
| **Site Engineer** | `engineer@onsiteerp.com` | `admin123` |
| **Supervisor** | `supervisor@onsiteerp.com` | `admin123` |
| **Employee / Staff** | `employee@onsiteerp.com` | `admin123` |
| **Vendor / Supplier** | `vendor@onsiteerp.com` | `admin123` |
| **Subcontractor** | `subcon@onsiteerp.com` | `admin123` |
| **Client** | `client@onsiteerp.com` | `admin123` |
| **Labour** | `labour@onsiteerp.com` | `admin123` |

---

## 3. Installation & Local Setup

### 1. Prerequisites
- **Python 3.8+** installed.
- **MongoDB** running locally on default port `27017` (or Atlas Cluster configured).

### 2. Install Dependencies
Initialize your virtual environment and install packages:
```bash
pip install -r requirements.txt
```

### 3. Setup Configuration
Ensure your `MONGO_URI` and `SECRET_KEY` are correct in the `.env` file:
```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-1234567890
MONGO_URI=mongodb://localhost:27017/construction_erp
```

### 4. Seed Database
Run the seeder to populate sample projects, materials, users, and procurement records:
```bash
python seed.py
```

### 5. Launch Server
Run the Flask development server:
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your web browser.

---

## 4. Project Folder Structure

- `app.py`: Main Flask entry point and Jinga helpers registration.
- `config.py`: Environment loader and size restrictions settings.
- `database/`: Connections initialization and index specifications.
- `routes/`: Blueprint controllers containing the 24 ERP routing files.
- `services/`: Business logic scripts (authentication, upload validation, inventory logs, invoice calculations, notifications).
- `utils/`: Enums, authorization decorators, alphanumeric generators.
- `templates/`: HTML5 views, Bootstrap layouts, modals, maps scripts.
- `static/`: Custom styling, scripts, uploaded file buffers.
