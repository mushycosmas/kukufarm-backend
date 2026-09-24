# KukuFarm Full Django REST API

This backend is organized by business domain instead of keeping all models in one `farm/models.py`.

## Apps

- accounts: authentication, users, roles
- flocks: flock management
- production: egg production
- feed: feed, purchases, stock
- health: health records, vaccinations, mortality
- customers: customers
- sales: sales and sale items
- expenses: expenses
- suppliers: suppliers
- reports: dashboard and analytics
- common: shared models and permissions

## Setup - Windows

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

## Demo login

Username: `admin`
Password: `admin123`

## Authentication

POST `/api/auth/login/`
```json
{"username":"admin","password":"admin123"}
```

Use:
`Authorization: Bearer <access>`

Refresh:
POST `/api/auth/refresh/`

Current user:
GET `/api/accounts/me/`

Roles:
GET `/api/accounts/roles/`

## API endpoints

### Accounts
- `/api/accounts/users/`
- `/api/accounts/me/`
- `/api/accounts/roles/`

### Flocks
- `/api/flocks/`

### Production
- `/api/production/eggs/`

### Feed
- `/api/feed/feeds/`
- `/api/feed/purchases/`
- `/api/feed/stock/`

### Health
- `/api/health/records/`
- `/api/health/vaccinations/`
- `/api/health/mortality/`

### Customers
- `/api/customers/`

### Sales
- `/api/sales/`

### Expenses
- `/api/expenses/`

### Suppliers
- `/api/suppliers/`

### Reports
- `/api/reports/dashboard/`
- `/api/reports/summary/`
- `/api/reports/production-chart/`

All ViewSet endpoints support normal GET/POST/PUT/PATCH/DELETE operations.

## React CRA

Create `.env` in the React project:

```env
REACT_APP_API_URL=http://127.0.0.1:8000/api
```

Axios:

```js
import axios from "axios";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://127.0.0.1:8000/api",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("kukufarm_access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

## PostgreSQL

Set in `.env`:

```env
DB_ENGINE=postgres
DB_NAME=kukufarm
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

Then:

```bash
python manage.py migrate
```

## Important

The frontend mock data should eventually be removed in favor of these API endpoints. Keep the API calls in a single React service layer so components do not directly manage Axios requests.
"# kukufarm-backend" 
