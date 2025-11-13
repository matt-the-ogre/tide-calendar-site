# CapRover Migration Assessment

## Executive Summary

This document assesses the migration of the Tide Calendar application from a dedicated Digital Ocean droplet to a CapRover-managed application. The migration is straightforward and will eliminate the need for manual nginx configuration while reducing operational costs.

**Migration Complexity:** Low
**Estimated Effort:** 1-2 hours
**Cost Savings:** High (consolidating from dedicated droplet to shared instance)

---

## Current Architecture (Digital Ocean Droplet)

### Deployment Stack
- **VM:** Dedicated Digital Ocean droplet (209.38.174.80)
- **Web Server:** nginx (SSL/TLS termination, reverse proxy)
- **Application:** Flask app in Docker container (port 5001)
- **Orchestration:** docker-compose
- **CI/CD:** GitHub Actions → SSH → deploy.sh script
- **Domain:** tidecalendar.xyz with Let's Encrypt SSL

### Current Files
```
Dockerfile                    # Flask app containerization
docker-compose.yaml          # Container orchestration
nginx.conf                   # Production nginx config (SSL, proxy)
nginx.dev.conf              # Development nginx config
deploy.sh                   # Deployment script (git pull, rebuild)
.github/workflows/deploy.yml # CI/CD automation
```

### Current Deployment Flow
1. Push to `main` branch triggers GitHub Actions
2. GitHub Actions SSH into droplet
3. Runs `deploy.sh` which:
   - Pulls latest code
   - Copies nginx config
   - Rebuilds Docker container via docker-compose
   - Reloads nginx

---

## Proposed Architecture (CapRover)

### Deployment Stack
- **Platform:** CapRover at https://captain.mattmanuel.ca
- **Web Server:** CapRover's built-in nginx reverse proxy (automatic)
- **Application:** Flask app in Docker container (port 80)
- **Orchestration:** CapRover (handles Docker automatically)
- **CI/CD:** GitHub webhook → CapRover (automatic deployment)
- **SSL/TLS:** CapRover handles via Let's Encrypt (automatic)

### Required Changes

#### 1. Files to CREATE
- **`captain-definition`** (required by CapRover)

#### 2. Files to MODIFY
- **`Dockerfile`** - Change port from 5001 to 80 (CapRover default)

#### 3. Files to REMOVE/DEPRECATE
- `nginx.conf` - No longer needed (CapRover handles reverse proxy)
- `nginx.dev.conf` - No longer needed
- `docker-compose.yaml` - No longer needed (CapRover handles orchestration)
- `deploy.sh` - No longer needed (webhook deployment)
- `.github/workflows/deploy.yml` - No longer needed (or disable for CapRover deployment)

---

## Detailed Migration Steps

### Phase 1: Prepare Repository

1. **Create captain-definition file:**
```json
{
  "schemaVersion": 2,
  "dockerfilePath": "./Dockerfile"
}
```

2. **Update Dockerfile:**
```diff
- EXPOSE 5001
+ EXPOSE 80
- ENV FLASK_RUN_PORT=5001
+ ENV FLASK_RUN_PORT=80
- CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
+ CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
```

3. **Update docker-compose.yaml (optional - for local dev only):**
```diff
  ports:
-   - "5001:5001"
+   - "5001:80"
  environment:
    FLASK_APP: run.py
    FLASK_ENV: production
-   FLASK_RUN_PORT: 5001
+   FLASK_RUN_PORT: 80
```

4. **Remove deprecated files:**
   - `nginx.conf`
   - `nginx.dev.conf`
   - `deploy.sh`

5. **Disable GitHub Actions deploy workflow:**
   - Either delete `.github/workflows/deploy.yml`
   - Or rename to `.github/workflows/deploy.yml.disabled`

### Phase 2: CapRover Configuration

1. **Create new app in CapRover:**
   - Login to https://captain.mattmanuel.ca
   - Create new app (e.g., "tide-calendar")
   - Enable HTTPS
   - Configure custom domain: tidecalendar.xyz

2. **Set up GitHub webhook:**
   - In CapRover app settings, get webhook URL
   - In GitHub repo settings → Webhooks → Add webhook
   - Set payload URL to CapRover webhook URL
   - Set content type to `application/json`
   - Select "Just the push event"
   - Trigger on pushes to `main` branch

3. **Configure environment variables in CapRover:**
   ```
   FLASK_APP=run.py
   FLASK_ENV=production
   FLASK_RUN_PORT=80
   ```

4. **Set persistent data (if needed):**
   - Configure persistent storage for SQLite database
   - Path in App: `/data`
   - Database file: `/data/tide_station_ids.db`

### Phase 3: Testing & Deployment

1. **Initial deployment:**
   - Push changes to a test branch first
   - Use CapRover's web interface to deploy manually
   - Verify app functionality

2. **Configure domain:**
   - Point tidecalendar.xyz DNS to CapRover instance
   - Enable HTTPS in CapRover (automatic Let's Encrypt)
   - Verify SSL certificate

3. **Test webhook deployment:**
   - Push to `main` branch
   - Verify automatic deployment via webhook
   - Check application health

4. **Decommission old droplet:**
   - Once verified, shut down old droplet
   - Cancel droplet billing

---

## Technical Considerations

### Port Configuration
- **Current:** Flask runs on port 5001, nginx proxies from 443→5001
- **CapRover:** Flask should run on port 80, CapRover proxies from 443→80
- **Alternative:** CapRover can be configured for custom ports if needed

### Static Files
- Current nginx serves `/static/` and `/ads.txt` directly
- Flask already serves these files
- CapRover will proxy all requests to Flask (no change needed)

### Database Persistence
- Current: SQLite database in `/app/tide_station_ids.db`
- CapRover: Configure persistent volume to preserve database across deployments
- Path mapping: `/data` → persistent storage
- Database file: `/data/tide_station_ids.db`

### Environment Variables
- Current: Set via docker-compose.yaml
- CapRover: Set via web UI or app definition
- Same variables needed: `FLASK_APP`, `FLASK_ENV`, `FLASK_RUN_PORT`

### PDF Generation
- Dependencies `pcal` and `ghostscript` installed via Dockerfile
- No changes needed - Dockerfile handles this
- CapRover will build container with these dependencies

---

## Benefits of Migration

### Cost Savings
- **Before:** Dedicated $6-12/month droplet for single app
- **After:** Share larger droplet ($24/month) with multiple apps
- **Savings:** ~$6-12/month per app consolidated

### Operational Benefits
- **No manual nginx configuration:** CapRover handles reverse proxy automatically
- **Automatic SSL:** Let's Encrypt certificates managed by CapRover
- **Easier deployments:** Webhook-based deployment (no SSH keys or GitHub Actions)
- **Built-in monitoring:** CapRover provides app health monitoring and logs
- **One-click rollbacks:** Easy to revert to previous deployments
- **No server maintenance:** CapRover handles container orchestration

### Developer Experience
- **Simpler repository:** Remove nginx configs, deploy scripts, docker-compose
- **Faster deployments:** Webhook triggers are faster than GitHub Actions + SSH
- **Better logging:** Centralized logging in CapRover UI
- **Environment management:** Easier to manage env vars via web UI

---

## Risks & Mitigation

### Risk: DNS cutover downtime
- **Mitigation:** Prepare DNS changes in advance, use low TTL before migration

### Risk: Database data loss
- **Mitigation:** Backup SQLite database before migration, test restore process

### Risk: Webhook configuration issues
- **Mitigation:** Test webhook with non-production branch first

### Risk: Port compatibility issues
- **Mitigation:** Test port 80 configuration locally before deploying

---

## Questions & Considerations

1. **Database backup strategy:**
   - Current backup process on droplet?
   - Need automated backups in CapRover?

2. **Traffic/usage patterns:**
   - What's the expected traffic?
   - Any specific performance requirements?

3. **Domain DNS:**
   - Who manages tidecalendar.xyz DNS?
   - Ready to update A records?

4. **Rollback plan:**
   - Keep old droplet running during testing period?
   - Define success criteria before decommissioning?

5. **Other apps on shared droplet:**
   - What else is running on the CapRover instance?
   - Resource allocation concerns?

---

## Recommended Next Steps

1. **Immediate:**
   - Review this assessment
   - Answer questions above
   - Decide on testing strategy

2. **Phase 1 (Preparation):**
   - Create captain-definition file
   - Update Dockerfile for port 80
   - Test build locally
   - Backup production database

3. **Phase 2 (Deploy to CapRover):**
   - Create CapRover app
   - Deploy via web UI initially
   - Configure domain and SSL
   - Set up webhook

4. **Phase 3 (Cutover):**
   - Update DNS
   - Test production traffic
   - Monitor for 24-48 hours
   - Decommission old droplet

---

## Conclusion

The migration from Digital Ocean droplet to CapRover is **highly recommended**. The technical changes are minimal, the operational benefits are significant, and cost savings are immediate. The application is well-suited for CapRover deployment with its simple Docker-based architecture.

**Complexity:** Low
**Risk:** Low
**Effort:** 1-2 hours
**ROI:** High (cost savings + operational simplification)
