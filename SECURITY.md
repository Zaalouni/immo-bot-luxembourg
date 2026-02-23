# Security Hardening - Production Deployment Checklist

## Overview

This document provides a comprehensive security review and deployment checklist for immo-bot-luxembourg v2.7+. The bot scrapes Luxembourg real estate listings and notifies via Telegram, requiring careful handling of sensitive data.

## Security Status

### ✅ Protected Areas

| Category | Status | Implementation |
|----------|--------|-----------------|
| **SQL Injection** | ✅ Protected | All queries use parameterized statements (?) |
| **XSS/HTML Injection** | ✅ Protected | HTML escaping in Telegram messages |
| **ReDoS Attacks** | ✅ Protected | Bounded regex patterns, input size limits |
| **Secret Masking** | ✅ Protected | `redact_secrets()` utility masks tokens/IDs |
| **Database Permissions** | ✅ Protected | listings.db set to 0o600 (read-only to owner) |
| **Configuration Validation** | ✅ Protected | GPS bounds, numeric range validation |
| **HTTPS Verification** | ✅ Protected | Explicit `verify=True` on all requests |
| **Error Message Sanitization** | ✅ Protected | Secrets redacted before logging/external exposure |

### ⚠️ Considerations for Deployment

| Area | Consideration | Mitigation |
|------|----------------|-----------|
| **Token Storage** | Telegram bot token in `.env` file | Keep `.env` out of version control, restrict file permissions |
| **Database Encryption** | SQLite data in plaintext | Consider SQLCipher for sensitive environments |
| **Log File Access** | Logs may contain sensitive data | Restrict log file permissions, monitor access |
| **Rate Limiting** | Random delays prevent aggressive detection | Monitor for patterns, adjust delays if needed |
| **Scraper Legitimacy** | User-Agent rotation may not fool advanced detection | Use responsible scraping practices, respect robots.txt |

## Pre-Deployment Security Checklist

### 1. Environment Configuration

- [ ] `.env` file created with correct values:
  - [ ] `TELEGRAM_BOT_TOKEN` set (starts with digits, contains 35+ chars)
  - [ ] `TELEGRAM_CHAT_ID` set (numeric or comma-separated list)
  - [ ] Other config values (prices, rooms, cities) validated

- [ ] `.env` file permissions secured:
  ```bash
  chmod 600 .env
  ```

- [ ] `.env` is in `.gitignore`:
  ```bash
  grep ".env" .gitignore
  ```

- [ ] Git history checked for leaked credentials:
  ```bash
  git log -p | grep -i "token\|secret\|password" || echo "✅ Clean"
  ```

### 2. Database Security

- [ ] First run creates `listings.db` with permissions 0o600:
  ```bash
  python -c "from database import db" && ls -la listings.db | grep rw---
  ```

- [ ] Database file is not world-readable:
  ```bash
  test $(stat -c %a listings.db) = "600" && echo "✅ Secure" || echo "❌ Fix permissions"
  ```

### 3. Log Security

- [ ] Log files do not contain secrets:
  ```bash
  grep -i "token\|secret\|[0-9]\{35,\}" immo_bot.log | head -5
  # Should show no matches or only redacted content
  ```

- [ ] Log file permissions secured:
  ```bash
  chmod 600 immo_bot.log
  ```

- [ ] Rotation is working (maxBytes=5MB, backupCount=3):
  ```bash
  ls -la immo_bot.log* | wc -l  # Should have up to 4 files
  ```

### 4. Configuration Validation

- [ ] GPS reference point is within Luxembourg:
  ```bash
  python -c "from config import REFERENCE_LAT, REFERENCE_LNG; print(f'({REFERENCE_LAT}, {REFERENCE_LNG})')"
  # Should show coordinates between 49.3-50.2°N, 5.7-6.6°E
  ```

- [ ] Price range is valid (MIN < MAX):
  ```bash
  python -c "from config import MIN_PRICE, MAX_PRICE; assert MIN_PRICE < MAX_PRICE; print(f'✅ {MIN_PRICE}€ - {MAX_PRICE}€')"
  ```

- [ ] Room range is valid (MIN < MAX):
  ```bash
  python -c "from config import MIN_ROOMS, MAX_ROOMS; assert MIN_ROOMS < MAX_ROOMS; print(f'✅ {MIN_ROOMS} - {MAX_ROOMS} rooms')"
  ```

### 5. HTTP Security

- [ ] All scrapers use HTTPS:
  ```bash
  grep -r "http://" scrapers/ | grep -v "https://" | wc -l
  # Should be 0 (only HTTPS URLs in production)
  ```

- [ ] Requests have explicit SSL verification:
  ```bash
  grep -r "requests.get\|requests.post" *.py scrapers/ | grep -v "verify=True" | wc -l
  # Should be 0 (all requests must have verify=True)
  ```

### 6. Test Data Validation

Run the bot in test mode to verify security:

```bash
# Single cycle test (no continuous loop)
python main.py --once

# Check for any exposed secrets in logs
grep -i "token\|secret\|chat.*id" immo_bot.log

# Verify database was created securely
ls -la listings.db

# Check that listings contain only valid GPS data
python -c "from database import db; import json; result = db.cursor.execute('SELECT COUNT(*) FROM listings WHERE latitude NOT BETWEEN 49.3 AND 50.2').fetchone(); print(f'Out-of-bounds GPS: {result[0]} - should be 0')"
```

## Security Incident Response

### If Token Exposed

1. Immediate: Revoke token in Telegram BotFather
2. Generate new token
3. Update `.env` with new token
4. Check logs for unauthorized access patterns
5. Review git history for token exposure

### If Database Compromised

1. Create new database with clean listings
2. Verify file permissions are 0o600
3. Review git history for database file access
4. Check for suspicious listing modifications

### If Logs Contain Secrets

1. Rotate logs: `rm immo_bot.log*`
2. Verify redaction is working: `grep -i "token\|secret" immo_bot.log` should show no actual values
3. Check if secrets were accessed in time window

## Security Hardening Summary

### v2.7 Delivered (Phases 1-3)

✅ **Input Validation**: Comprehensive `validate_listing_data()` function
✅ **Regex Safety**: Bounded patterns prevent ReDoS
✅ **Bot Evasion**: User-Agent rotation, random delays

### v2.7 Follow-up Completed (Phases 4+)

✅ **Secret Masking**: `redact_secrets()` redacts tokens/IDs from logs
✅ **Error Sanitization**: Exception messages sanitized before external exposure
✅ **Database Hardening**: File permissions set to 0o600
✅ **Configuration Validation**: GPS bounds, numeric ranges validated
✅ **HTTPS Verification**: All requests explicitly set `verify=True`

## Maintenance & Monitoring

### Regular Tasks

- **Weekly**: Review logs for errors, check for repeated failures
- **Monthly**: Verify database file permissions, check disk usage
- **Quarterly**: Review security dependencies, check for updates
- **Yearly**: Rotate Telegram token proactively

### Monitoring Recommendations

- Set up alerts for repeated scraper failures
- Monitor disk usage (database growth)
- Track rate limit occurrences
- Monitor system resource usage

## References

### Key Files

| File | Purpose | Security Relevance |
|------|---------|-------------------|
| config.py | Configuration loading | Token/GPS validation |
| database.py | SQLite persistence | File permissions |
| utils.py | Utilities & validation | Redaction, GPS validation |
| main.py | Orchestration | Error sanitization |
| notifier.py | Telegram API | Token handling, HTTPS |

### Functions

- `redact_secrets(text)` in utils.py: Masks sensitive data in logs
- `validate_listing_gps(listing)` in utils.py: Validates GPS coordinates
- `validate_listing_data(listing)` in utils.py: Comprehensive input validation
- `_validate_gps_coords(lat, lng)` in config.py: GPS bounds validation

## Deployment Verification Checklist

Before going to production:

```bash
#!/bin/bash
# Pre-deployment security verification

echo "🔐 Security Pre-Deployment Checklist"
echo "===================================="

# 1. Check .env exists and has correct permissions
test -f .env && chmod 600 .env && echo "✅ .env configured" || echo "❌ .env missing"

# 2. Check .env is in .gitignore
grep -q "\.env" .gitignore && echo "✅ .env in .gitignore" || echo "❌ Add .env to .gitignore"

# 3. Run config validation
python -c "from config import *; print('✅ Configuration valid')" || echo "❌ Config error"

# 4. Check for hardcoded secrets in code
! grep -r "token\|secret\|password" . --include="*.py" | grep -v "TELEGRAM_BOT_TOKEN\|redact_secrets" && echo "✅ No hardcoded secrets" || echo "⚠️ Review matched lines"

# 5. Test single cycle
python main.py --once > /tmp/test.log 2>&1 && echo "✅ Bot runs successfully" || echo "❌ Bot error"

# 6. Check logs for exposed secrets
! grep -i "^[0-9]\{6,\}:[A-Za-z0-9_-]\{35,\}" immo_bot.log && echo "✅ No exposed tokens in logs" || echo "❌ Token exposed!"

# 7. Verify database permissions
test $(stat -c %a listings.db 2>/dev/null || stat -f %A listings.db 2>/dev/null) = "600" && echo "✅ Database secure" || echo "⚠️ Check permissions"

echo ""
echo "Ready for deployment! 🚀"
```

## Support & Questions

For security concerns or questions, refer to:
- architecture.md: System design and data flow
- planning.md: Feature roadmap and known issues
- Test mode: `python main.py --once` for safe testing

---

**Last Updated**: 2026-02-23
**Version**: v2.7+ Security Hardening
**Status**: Production Ready
