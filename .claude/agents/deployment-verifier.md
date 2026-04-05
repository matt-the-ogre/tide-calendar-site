---
name: deployment-verifier
description: Verify a CapRover deployment succeeded by checking container status, generating a test PDF, and validating the output
---

# Deployment Verifier

Verify that a CapRover deployment completed successfully and the application works correctly.

## Arguments
- Environment: `dev` or `prod` (required)

## Tools Available
- Bash (for SSH and curl commands)
- Read (for inspecting downloaded files)

## Steps

1. **Check container status**: Verify the container was recently recreated
   ```bash
   ssh captain "docker ps --format '{{.Names}} {{.CreatedAt}}' | grep tide-calendar-${ENV}"
   ```
   Confirm the creation timestamp is recent (within the last 5 minutes).

2. **Health check**: Verify the site responds
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://${DOMAIN}/
   ```
   - dev: `dev.tidecalendar.xyz`
   - prod: `tidecalendar.xyz`

3. **Clear PDF cache**: Remove stale cached PDFs to ensure fresh generation
   ```bash
   ssh captain "docker exec ${CONTAINER} sh -c 'rm -f /data/calendars/*.pdf'"
   ```

4. **Generate test PDF**: Submit the form for the default demo station (Point Roberts, WA - 9449639)
   ```bash
   curl -s -o /tmp/deploy-verify.pdf -w "%{http_code}" \
     -X POST https://${DOMAIN}/ \
     -d "country_filter=all&station_search=Point+Roberts%2C+WA&station_id=&year=2026&month=04"
   ```
   Confirm HTTP 200 and non-empty PDF response.

5. **Validate PDF content**: Check file size is reasonable (>8000 bytes indicates mini-calendars present)
   ```bash
   wc -c /tmp/deploy-verify.pdf
   ```

6. **Report results**:
   - Container creation time
   - Health check status
   - PDF generation status
   - PDF file size
   - Overall: PASS or FAIL
