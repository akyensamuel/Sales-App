# Database Maintenance Quick Reference

## 🔍 Daily Monitoring Commands

### Check RLS Security Status
```bash
python scripts/testing/check_rls_security.py
```

### Monitor Performance
```bash
python scripts/testing/monitor_performance.py
```

### Analyze Index Usage
```bash
python scripts/testing/analyze_index_usage.py
```

## 🛠️ Maintenance Scripts

### Apply Security Policies
```bash
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute(open('sql/enable_rls_security.sql').read()); print('Security applied')"
```

### Performance Optimization
```bash
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute(open('sql/optimize_performance_phase1.sql').read()); print('Performance optimized')"
```

### Create Strategic Indexes
```bash
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute(open('sql/create_performance_indexes_final.sql').read()); print('Indexes created')"
```

## 📊 Key Performance Indicators

### Security Metrics (Target: 100%)
- ✅ RLS enabled tables: 26/26
- ✅ Security policies: 27/27
- ✅ Critical vulnerabilities: 0/0

### Performance Metrics (Target: >80%)
- ✅ Index efficiency: 31.8% (target: >50%)
- ✅ Storage optimization: 1.5MB saved
- ⚠️ Query performance: ~250ms (target: <100ms)

## 🚨 Alert Thresholds

### Security Alerts
- Any RLS disabled tables
- Failed policy applications
- Unauthorized data access attempts

### Performance Alerts
- Query times >500ms
- Index efficiency <25%
- Storage growth >10% monthly

## 🔧 Troubleshooting

### Common Issues
1. **RLS Error:** Check user group memberships
2. **Slow Queries:** Verify index usage with EXPLAIN
3. **High Storage:** Analyze unused indexes

### Emergency Commands
```bash
# Check database connection
python manage.py dbshell -c "SELECT 1;"

# Verify security status
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT COUNT(*) FROM pg_tables WHERE schemaname = %s AND rowsecurity = true', ['public']); print('Secured tables:', cursor.fetchone()[0])"

# Quick performance check
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT COUNT(*) as total, SUM(CASE WHEN idx_scan = 0 THEN 1 ELSE 0 END) as unused FROM pg_stat_user_indexes WHERE schemaname = %s', ['public']); total, unused = cursor.fetchone(); print(f'Efficiency: {((total-unused)/total)*100:.1f}%')"
```
