# Maintenance Mode Guide

## How to Enable Maintenance Mode

When you need to update the website and want to show a maintenance page instead of the trading dashboard:

### Method 1: Using Environment Variable (Recommended)

1. SSH into the server:
   ```bash
   ssh root@47.77.195.172
   ```

2. Edit the frontend .env file:
   ```bash
   cd /root/grid-trading-battle/frontend
   nano .env
   ```

3. Change `VITE_MAINTENANCE_MODE=false` to `VITE_MAINTENANCE_MODE=true`

4. Rebuild and deploy the frontend:
   ```bash
   npm run build
   rm -rf /var/www/grid-trading/*
   cp -r dist/* /var/www/grid-trading/
   systemctl reload nginx
   ```

### Method 2: Quick Toggle (From Local Machine)

```bash
# Enable maintenance mode
sshpass -p 'Aa112211.' ssh root@47.77.195.172 "cd /root/grid-trading-battle/frontend && sed -i 's/VITE_MAINTENANCE_MODE=false/VITE_MAINTENANCE_MODE=true/' .env && npm run build && rm -rf /var/www/grid-trading/* && cp -r dist/* /var/www/grid-trading/ && systemctl reload nginx"

# Disable maintenance mode
sshpass -p 'Aa112211.' ssh root@47.77.195.172 "cd /root/grid-trading-battle/frontend && sed -i 's/VITE_MAINTENANCE_MODE=true/VITE_MAINTENANCE_MODE=false/' .env && npm run build && rm -rf /var/www/grid-trading/* && cp -r dist/* /var/www/grid-trading/ && systemctl reload nginx"
```

## What Users See

When maintenance mode is enabled, users will see:
- A clean maintenance page with a construction icon
- Message: "Website Under Maintenance"
- Description: "We're currently updating our platform to bring you a better experience"
- Link to Twitter: @algoarena
- No "Failed to fetch" errors
- No access to the trading dashboard

## Features

- **No Error Messages**: The maintenance page replaces all error messages
- **Professional Look**: Clean, modern design with your branding
- **Social Media Link**: Directs users to Twitter for updates
- **Instant Activation**: Takes effect immediately after deployment

## Twitter Link

The maintenance page includes a link to: https://twitter.com/algoarena

Make sure to update this link in `/root/grid-trading-battle/frontend/src/components/MaintenancePage.tsx` if you want to use a different Twitter handle.
