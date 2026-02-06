# Pattern Storage Configuration for Render

The smart email pattern learning system stores learned patterns to improve performance over time. However, Render's filesystem is **ephemeral** - any files written during runtime are lost when the container restarts.

## Current Behavior (Memory-Only Mode)

✅ **Pattern learning works** during runtime
✅ **Fast-track mode activates** when confidence >75%
✅ **No error logs** (permission errors are silently handled)
❌ **Patterns lost** on server restart/redeploy

## Production Solutions

### Option 1: PostgreSQL (Recommended for Render)

Add pattern storage to your existing database:

```sql
CREATE TABLE email_patterns (
    domain VARCHAR(255) PRIMARY KEY,
    pattern VARCHAR(50) NOT NULL,
    success_count INTEGER DEFAULT 1,
    total_attempts INTEGER DEFAULT 1,
    confidence DECIMAL(5,4) DEFAULT 1.0,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    example_email VARCHAR(255)
);
CREATE INDEX idx_confidence ON email_patterns(confidence DESC);
```

Then update `pattern_engine.py` to use DB instead of JSON file.

### Option 2: Render Disk (Persistent Storage)

Add a persistent disk to your Render service:

1. Go to Render Dashboard → Your Service → Disks
2. Add Disk: Mount Path = `/data`, Size = 1GB
3. Set environment variable: `PATTERN_STORAGE_PATH=/data/email_patterns.json`
4. Update `pattern_engine.py`:
   ```python
   _STORAGE_PATH = Path(os.getenv('PATTERN_STORAGE_PATH', 'data/email_patterns.json'))
   ```

**Cost:** ~$0.25/month for 1GB disk

### Option 3: Redis (Fast & Simple)

Use Render's Redis add-on:

1. Add Redis to your service (free tier available)
2. Install: `pip install redis`
3. Update pattern engine to use Redis instead of JSON

### Option 4: Accept Memory-Only Mode

For small-scale usage, memory-only mode is acceptable:
- Patterns re-learn quickly (1-2 contacts per domain)
- No infrastructure changes needed
- Works immediately after deployment

## Current Status

✅ System is running in **memory-only mode**
✅ Logs are clean (no more permission errors)
✅ Pattern learning works during runtime
⚠️ Patterns reset on container restart

## Recommendation

**For production at scale:** Use Option 1 (PostgreSQL) - you likely already have a database
**For quick fix:** Use Option 2 (Render Disk) - cheapest persistent solution
**For now:** Memory-only mode works fine, patterns re-learn automatically
