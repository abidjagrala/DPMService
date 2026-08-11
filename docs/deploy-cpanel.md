# Deploy to cPanel — Step-by-Step Guide

## Prerequisites

- cPanel account with Python app support (Phusion Passenger)
- SSH access or Git deployment enabled
- MySQL database created in cPanel
- Domain pointed to cPanel (e.g. `dpm.dnscloud.in`)

---

## 1. Initial cPanel Setup

### Create Python App
1. Log in to cPanel
2. Go to **Software** → **Setup Python App**
3. Click **Create Application**
   - Python version: **3.10**
   - Application root: **dpm.dnscloud.in** (or your domain folder)
   - Application URL: select your domain
   - Application startup file: **passenger_wsgi.py**
4. Click **Create**

### Create MySQL Database
1. Go to **Databases** → **MySQL Databases**
2. Create a new database (e.g. `dhmahqqz_dpm`)
3. Create a new user with a strong password
4. Add the user to the database with **All Privileges**

---

## 2. Environment Variables

In cPanel → **Software** → **Setup Python App** → click your app → **Environment Variables**:

| Variable | Value |
|---|---|
| `DJANGO_MODE` | `production` |
| `DEBUG` | `False` |
| `SECRET_KEY` | *(generate a new one)* |
| `DB_NAME` | `dhmahqqz_dpm` |
| `DB_USER` | `dhmahqqz_dpmuser` |
| `DB_PASSWORD` | *(your db password)* |
| `DB_HOST` | `127.0.0.1` |
| `DB_PORT` | `3306` |
| `ALLOWED_HOSTS` | `dpm.dnscloud.in` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | *(your email)* |
| `EMAIL_HOST_PASSWORD` | *(app password)* |
| `DEFAULT_FROM_EMAIL` | `DPM Service <noreply@dpm.com>` |

---

## 3. Git Deployment (Recommended)

### Connect Repository
1. Go to cPanel → **Version Control** (or **Git Version Control**)
2. Click **Create Repository**
   - Repository URL: `https://github.com/abidjagrala/DPMService.git`
   - Branch: `main`
   - Deployment path: `dpm.dnscloud.in`

### Enable Auto-Deploy
1. In your repository settings, enable **Auto Deploy**
2. Every push to `main` will trigger `.cpanel.yml` tasks:
   ```
   pip install -r requirements.txt
   python manage.py migrate --noinput
   python manage.py seed_authorization
   python manage.py collectstatic --noinput
   ```

### First Deploy
After the first git pull, you may need to manually run:
```bash
source /home/dhmahqqz/virtualenv/dpm.dnscloud.in/3.10/bin/activate
cd dpm.dnscloud.in
python manage.py createsuperuser
```

### After Every Deploy
```bash
source /home/dhmahqqz/virtualenv/dpm.dnscloud.in/3.10/bin/activate
cd dpm.dnscloud.in
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py shell -c "from authorization.services.permission_engine import clear_all_permissions; clear_all_permissions()"
touch dpmservice/wsgi.py
```

---

## 4. Manual Deployment (Alternative)

If not using Git, upload files via File Manager or SSH:

```bash
# SSH into cPanel
ssh dpm.dnscloud.in

# Navigate to app directory
cd ~/dpm.dnscloud.in

# Activate virtualenv
source ~/virtualenv/dpm.dnscloud.in/3.10/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --noinput

# Seed authorization
python manage.py seed_authorization

# Collect static files
python manage.py collectstatic --noinput

# Create admin user
python manage.py createsuperuser
```

---

## 5. Post-Deployment Checklist

- [ ] Static files served correctly (`/static/` URL)
- [ ] Media files accessible (`/media/` URL)
- [ ] Admin panel accessible (`/admin/`)
- [ ] Login page works
- [ ] Database migrations applied
- [ ] Permission cache cleared after deployment
- [ ] Authorization modules seeded (via admin UI or `seed_authorization`)
- [ ] `.env` file NOT in repository (use cPanel Environment Variables)
- [ ] `DEBUG=False` in production
- [ ] `ALLOWED_HOSTS` includes your domain

---

## 6. Troubleshooting

### Application Error (500)
- Check cPanel → **Error Logs**
- Verify `DJANGO_MODE=production` is set
- Verify MySQL database credentials are correct

### Static Files Not Loading
- Run `python manage.py collectstatic --noinput` manually
- Check `STATIC_ROOT` setting points to `staticfiles/`

### Database Connection Error
- Verify MySQL database exists in cPanel
- Check `DB_HOST` is `127.0.0.1` (not `localhost`)
- Ensure user has **All Privileges** on the database

### Migration Errors
- SSH in and run `python manage.py migrate --noinput` manually
- Check for migration conflicts: `python manage.py showmigrations`

---

## 7. Key Files

| File | Purpose |
|---|---|
| `.cpanel.yml` | Auto-deploy tasks on git push |
| `passenger_wsgi.py` | cPanel Python app entry point |
| `dpmservice/wsgi.py` | Django WSGI application |
| `dpmservice/settings.py` | Django settings (reads from env vars) |
| `requirements.txt` | Python dependencies |
