---
name: clear-cache
description: Clear PDF cache on dev or prod CapRover container. Usage: /clear-cache dev or /clear-cache prod
---

# Clear PDF Cache

Clear cached PDF calendars from a CapRover environment.

## Arguments
- First argument: `dev` or `prod` (required)

## Steps

1. Determine the environment from the argument (`dev` or `prod`). If not provided, ask.
2. Find the container:
   ```bash
   ssh captain "docker ps --format '{{.Names}}' | grep tide-calendar-${ENV}"
   ```
3. List current cache contents:
   ```bash
   ssh captain "docker exec ${CONTAINER} sh -c 'ls /data/calendars/*.pdf 2>/dev/null | wc -l'"
   ```
4. Clear the cache:
   ```bash
   ssh captain "docker exec ${CONTAINER} sh -c 'rm -f /data/calendars/*.pdf'"
   ```
5. Confirm deletion by listing the directory again.
6. Report how many PDFs were removed.

**Important**: Must use `sh -c` wrapper for glob expansion inside `docker exec`.
