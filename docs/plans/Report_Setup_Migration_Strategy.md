# Report Setup - Migration and Rollout Strategy

## Overview

This document outlines the safe migration and rollout strategy for the Report Setup feature, ensuring zero downtime and no impact on existing functionality.

## Migration Principles

1. **Additive Only**: Only add new tables/columns, never modify existing ones
2. **Feature Flags**: Control feature visibility and rollout
3. **Backward Compatible**: Maintain compatibility with existing systems
4. **Reversible**: All changes can be rolled back safely
5. **Incremental**: Deploy in phases with validation at each step

## Database Migration Plan

### Phase 1: Schema Addition (No Risk)

```sql
-- Migration: 001_add_report_setup_tables.sql
BEGIN;

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Report Templates Table
CREATE TABLE IF NOT EXISTS report_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    blocks JSONB NOT NULL DEFAULT '[]',
    variables JSONB DEFAULT '{}',
    data_requirements JSONB DEFAULT '{}',
    scoring_categories JSONB DEFAULT '[]',
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    parent_version_id UUID REFERENCES report_templates(id),
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_template_name_version UNIQUE (name, version)
);

-- Indexes for performance
CREATE INDEX idx_report_templates_name ON report_templates(name);
CREATE INDEX idx_report_templates_category ON report_templates(category);
CREATE INDEX idx_report_templates_is_active ON report_templates(is_active);
CREATE INDEX idx_report_templates_created_by ON report_templates(created_by);

-- 2. Report Generation Jobs Table
CREATE TABLE IF NOT EXISTS report_generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES report_templates(id),
    configuration JSONB NOT NULL,
    scan_data_ids JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    stage VARCHAR(50),
    message TEXT,
    results JSONB,
    error_details JSONB,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

-- Indexes
CREATE INDEX idx_report_jobs_status ON report_generation_jobs(status);
CREATE INDEX idx_report_jobs_created_by ON report_generation_jobs(created_by);
CREATE INDEX idx_report_jobs_created_at ON report_generation_jobs(created_at DESC);

-- 3. Generated Reports Table
CREATE TABLE IF NOT EXISTS generated_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES report_generation_jobs(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES report_templates(id),
    title VARCHAR(500) NOT NULL,
    formats JSONB NOT NULL DEFAULT '[]',
    file_paths JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    size_bytes BIGINT,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_generated_reports_job_id ON generated_reports(job_id);
CREATE INDEX idx_generated_reports_created_by ON generated_reports(created_by);
CREATE INDEX idx_generated_reports_created_at ON generated_reports(created_at DESC);

-- 4. Report Schedules Table
CREATE TABLE IF NOT EXISTS report_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    template_id UUID NOT NULL REFERENCES report_templates(id),
    configuration JSONB NOT NULL,
    data_selection JSONB NOT NULL,
    schedule_type VARCHAR(50) NOT NULL,
    schedule_config JSONB NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT true,
    next_run TIMESTAMP WITH TIME ZONE,
    last_run TIMESTAMP WITH TIME ZONE,
    last_job_id UUID REFERENCES report_generation_jobs(id),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_schedule_type CHECK (schedule_type IN ('once', 'daily', 'weekly', 'monthly', 'cron'))
);

-- Indexes
CREATE INDEX idx_report_schedules_is_active ON report_schedules(is_active);
CREATE INDEX idx_report_schedules_next_run ON report_schedules(next_run);
CREATE INDEX idx_report_schedules_created_by ON report_schedules(created_by);

-- 5. Block Registry Table (for dynamic blocks)
CREATE TABLE IF NOT EXISTS report_block_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    block_id VARCHAR(100) UNIQUE NOT NULL,
    block_name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    configuration_schema JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
```

### Phase 2: Migration Verification

```python
# scripts/verify_report_migration.py
import asyncio
from sqlalchemy import select, inspect
from app.db.database import get_session

async def verify_migration():
    """Verify report setup tables were created correctly"""

    async with get_session() as db:
        inspector = inspect(db.bind)

        required_tables = [
            'report_templates',
            'report_generation_jobs',
            'generated_reports',
            'report_schedules',
            'report_block_registry'
        ]

        existing_tables = inspector.get_table_names()

        print("Migration Verification:")
        print("-" * 50)

        all_present = True
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ {table} - Created successfully")

                # Check indexes
                indexes = inspector.get_indexes(table)
                print(f"   Indexes: {len(indexes)}")

                # Check constraints
                constraints = inspector.get_check_constraints(table)
                print(f"   Constraints: {len(constraints)}")
            else:
                print(f"❌ {table} - Missing!")
                all_present = False

        print("-" * 50)

        if all_present:
            print("✅ All tables created successfully!")
            return True
        else:
            print("❌ Some tables are missing!")
            return False

if __name__ == "__main__":
    asyncio.run(verify_migration())
```

## Setup Script Updates

### Safe Setup Script Integration

```bash
#!/bin/bash
# setup_report_features.sh

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Report Setup Feature Installation${NC}"
echo "===================================="

# Check if running in Docker or local
if [ -f "/.dockerenv" ]; then
    IN_DOCKER=true
else
    IN_DOCKER=false
fi

# Function to check if PostgreSQL is ready
check_postgres() {
    echo -n "Checking PostgreSQL connection..."

    if [ "$IN_DOCKER" = true ]; then
        pg_isready -h postgres -U $POSTGRES_USER
    else
        docker exec -i violentutf-postgres pg_isready -U $POSTGRES_USER
    fi

    if [ $? -eq 0 ]; then
        echo -e " ${GREEN}✓${NC}"
        return 0
    else
        echo -e " ${RED}✗${NC}"
        return 1
    fi
}

# Function to check if tables exist
check_tables_exist() {
    local query="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('report_templates', 'report_generation_jobs', 'generated_reports', 'report_schedules');"

    if [ "$IN_DOCKER" = true ]; then
        count=$(psql -h postgres -U $POSTGRES_USER -d $POSTGRES_DB -tAc "$query")
    else
        count=$(docker exec -i violentutf-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -tAc "$query")
    fi

    echo $count
}

# Function to run migration
run_migration() {
    echo "Running database migration..."

    if [ "$IN_DOCKER" = true ]; then
        cd /app && alembic upgrade head
    else
        docker exec -i violentutf-api sh -c "cd /app && alembic upgrade head"
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migration completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Migration failed${NC}"
        return 1
    fi
}

# Function to load initial templates
load_initial_templates() {
    echo "Loading initial report templates..."

    if [ "$IN_DOCKER" = true ]; then
        python /app/scripts/load_initial_templates.py
    else
        docker exec -i violentutf-api python /app/scripts/load_initial_templates.py
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Templates loaded successfully${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Template loading failed (non-critical)${NC}"
        return 0  # Don't fail setup
    fi
}

# Function to enable feature flag
enable_feature_flag() {
    echo "Enabling Report Setup feature..."

    # Add to environment file
    if grep -q "REPORT_SETUP_ENABLED" violentutf/.env 2>/dev/null; then
        sed -i.bak 's/REPORT_SETUP_ENABLED=.*/REPORT_SETUP_ENABLED=true/' violentutf/.env
    else
        echo "REPORT_SETUP_ENABLED=true" >> violentutf/.env
    fi

    echo -e "${GREEN}✓ Feature flag enabled${NC}"
}

# Main installation flow
main() {
    echo "Starting Report Setup feature installation..."
    echo

    # Step 1: Check PostgreSQL
    if ! check_postgres; then
        echo -e "${RED}Error: PostgreSQL is not ready${NC}"
        exit 1
    fi

    # Step 2: Check if already installed
    existing_tables=$(check_tables_exist)

    if [ "$existing_tables" -eq "4" ]; then
        echo -e "${YELLOW}Report Setup tables already exist. Skipping migration.${NC}"
    else
        echo "Report Setup tables not found. Installing..."

        # Step 3: Run migration
        if ! run_migration; then
            echo -e "${RED}Migration failed! Aborting installation.${NC}"
            exit 1
        fi

        # Step 4: Verify migration
        new_count=$(check_tables_exist)
        if [ "$new_count" -ne "4" ]; then
            echo -e "${RED}Migration verification failed! Expected 4 tables, found $new_count${NC}"
            exit 1
        fi

        # Step 5: Load initial templates
        load_initial_templates
    fi

    # Step 6: Enable feature flag
    enable_feature_flag

    echo
    echo -e "${GREEN}Report Setup feature installation completed!${NC}"
    echo
    echo "Next steps:"
    echo "1. Restart the FastAPI service to load new endpoints"
    echo "2. Restart the Streamlit app to show the Report Setup page"
    echo "3. Access Report Setup at: http://localhost:8501/Report_Setup"
}

# Run main function
main
```

### Integration with Existing Setup Scripts

```bash
# In setup_macos_new.sh (and equivalents)

# Add after database initialization
echo "Checking for additional features..."

# Report Setup Feature
if [ -f "./scripts/setup_report_features.sh" ]; then
    echo "Found Report Setup feature installer"
    read -p "Install Report Setup feature? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./scripts/setup_report_features.sh
    else
        echo "Skipping Report Setup installation"
    fi
fi
```

## Rollout Strategy

### Phase 1: Internal Testing (Week 1)

1. **Deploy to Development**:
   - Run migration on dev database
   - Enable feature flag for dev team
   - Test all functionality

2. **Validation Checklist**:
   - [ ] All tables created successfully
   - [ ] No impact on existing Dashboard
   - [ ] API endpoints accessible
   - [ ] Streamlit page loads correctly
   - [ ] Basic report generation works

### Phase 2: Limited Beta (Week 2-3)

1. **Deploy to Staging**:
   ```bash
   # Enable for specific users
   REPORT_SETUP_ENABLED=true
   REPORT_SETUP_BETA_USERS=user1,user2,user3
   ```

2. **Beta Features**:
   ```python
   # In Streamlit navigation
   def should_show_report_setup(user):
       if not settings.REPORT_SETUP_ENABLED:
           return False

       if settings.REPORT_SETUP_BETA_USERS:
           beta_users = settings.REPORT_SETUP_BETA_USERS.split(',')
           return user.username in beta_users

       return True
   ```

3. **Monitoring**:
   - Track usage metrics
   - Collect user feedback
   - Monitor performance impact

### Phase 3: Gradual Rollout (Week 4-5)

1. **Percentage-Based Rollout**:
   ```python
   # Gradual rollout logic
   import hashlib

   def should_enable_for_user(username, rollout_percentage):
       """Deterministic rollout based on username"""
       hash_value = int(hashlib.md5(username.encode()).hexdigest(), 16)
       return (hash_value % 100) < rollout_percentage
   ```

2. **Rollout Schedule**:
   - Day 1-3: 10% of users
   - Day 4-7: 25% of users
   - Day 8-10: 50% of users
   - Day 11-14: 75% of users
   - Day 15: 100% (full rollout)

### Phase 4: Full Production (Week 6)

1. **Complete Enablement**:
   ```bash
   # Remove beta restrictions
   REPORT_SETUP_ENABLED=true
   REPORT_SETUP_BETA_USERS=
   ```

2. **Documentation Release**:
   - User guides published
   - Video tutorials available
   - Support team trained

## Rollback Plan

### Database Rollback

```sql
-- Rollback script: 001_rollback_report_setup.sql
BEGIN;

-- Drop tables in reverse order due to foreign keys
DROP TABLE IF EXISTS report_block_registry CASCADE;
DROP TABLE IF EXISTS report_schedules CASCADE;
DROP TABLE IF EXISTS generated_reports CASCADE;
DROP TABLE IF EXISTS report_generation_jobs CASCADE;
DROP TABLE IF EXISTS report_templates CASCADE;

COMMIT;
```

### Feature Flag Rollback

```bash
# Immediate disable
echo "REPORT_SETUP_ENABLED=false" >> violentutf/.env

# Restart services
docker-compose restart api streamlit
```

### Data Preservation

```bash
# Backup before rollback
pg_dump -h localhost -U $POSTGRES_USER -d $POSTGRES_DB \
    -t report_templates \
    -t report_generation_jobs \
    -t generated_reports \
    -t report_schedules \
    -t report_block_registry \
    > report_setup_backup_$(date +%Y%m%d_%H%M%S).sql
```

## Monitoring and Metrics

### Key Metrics to Track

1. **Performance Metrics**:
   ```python
   # Metrics collection
   class ReportMetrics:
       def __init__(self):
           self.generation_times = []
           self.template_usage = Counter()
           self.error_rates = defaultdict(int)

       async def track_generation(self, template_id, duration, success):
           self.generation_times.append(duration)
           self.template_usage[template_id] += 1
           if not success:
               self.error_rates[template_id] += 1
   ```

2. **Usage Metrics**:
   - Daily active users
   - Reports generated per day
   - Most used templates
   - Average generation time

3. **Error Tracking**:
   - Generation failure rate
   - API error responses
   - Database query performance

### Monitoring Dashboard

```python
# monitoring/report_setup_monitor.py
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func

async def generate_metrics_report():
    """Generate daily metrics report"""

    async with get_session() as db:
        # Report generation metrics
        yesterday = datetime.utcnow() - timedelta(days=1)

        # Total reports generated
        total_reports = await db.scalar(
            select(func.count(GeneratedReport.id))
            .where(GeneratedReport.created_at >= yesterday)
        )

        # Success rate
        successful_jobs = await db.scalar(
            select(func.count(ReportGenerationJob.id))
            .where(
                ReportGenerationJob.created_at >= yesterday,
                ReportGenerationJob.status == 'completed'
            )
        )

        total_jobs = await db.scalar(
            select(func.count(ReportGenerationJob.id))
            .where(ReportGenerationJob.created_at >= yesterday)
        )

        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0

        # Average generation time
        avg_time = await db.scalar(
            select(func.avg(
                func.extract('epoch',
                    ReportGenerationJob.completed_at - ReportGenerationJob.started_at
                )
            ))
            .where(
                ReportGenerationJob.status == 'completed',
                ReportGenerationJob.created_at >= yesterday
            )
        )

        print(f"Daily Report Setup Metrics - {datetime.utcnow().date()}")
        print("=" * 50)
        print(f"Total Reports Generated: {total_reports}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Average Generation Time: {avg_time:.2f} seconds")
```

## Communication Plan

### Pre-Launch Communication

1. **Internal Announcement** (2 weeks before):
   - Feature overview
   - Benefits and use cases
   - Timeline for rollout

2. **Documentation Release** (1 week before):
   - User guides
   - API documentation
   - Video tutorials

### Launch Communication

1. **Feature Announcement**:
   ```markdown
   # 🎉 Introducing Report Setup

   We're excited to announce the launch of Report Setup,
   a powerful new feature for generating professional
   security assessment reports from your scan data.

   **Key Features:**
   - 📊 Browse and select scan data
   - 📝 Choose from pre-built templates
   - ⚙️ Configure report parameters
   - 👁️ Preview before generation
   - 📤 Export to multiple formats

   **Getting Started:**
   Access Report Setup from the Advanced Dashboard menu.

   [View Documentation] [Watch Tutorial]
   ```

2. **Support Resources**:
   - FAQ document
   - Troubleshooting guide
   - Support ticket category

## Success Criteria

### Technical Success

1. **Performance**:
   - Report generation < 30 seconds (95th percentile)
   - API response time < 500ms (95th percentile)
   - Zero downtime during rollout

2. **Reliability**:
   - Success rate > 95%
   - Error rate < 1%
   - No impact on existing features

### Business Success

1. **Adoption**:
   - 50% of active users try feature within 30 days
   - 25% become regular users (weekly usage)
   - Positive user feedback > 80%

2. **Value Delivery**:
   - Time saved on report generation
   - Increased report consistency
   - Improved security insights

## Conclusion

This migration and rollout strategy ensures a safe, controlled deployment of the Report Setup feature with:

1. **Zero risk** to existing functionality
2. **Gradual rollout** with monitoring
3. **Clear rollback** procedures
4. **Comprehensive testing** at each phase
5. **Strong communication** and support

The additive-only approach to database changes and feature flag control provides maximum flexibility and safety throughout the deployment process.
