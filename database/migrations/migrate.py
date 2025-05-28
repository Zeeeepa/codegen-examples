#!/usr/bin/env python3
"""
Database Migration System for AI-Powered Development Workflow
Handles schema versioning, migration execution, and rollback capabilities
"""

import os
import sys
import logging
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handles database schema migrations with version control and rollback support"""
    
    def __init__(self, connection_string: str, schema_dir: str = "database/schema"):
        self.connection_string = connection_string
        self.schema_dir = Path(schema_dir)
        self.migration_table = "schema_migrations"
        
    def get_connection(self) -> psycopg2.extensions.connection:
        """Get database connection with proper configuration"""
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def ensure_migration_table(self) -> None:
        """Create migration tracking table if it doesn't exist"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.migration_table} (
            id SERIAL PRIMARY KEY,
            version VARCHAR(50) NOT NULL UNIQUE,
            filename VARCHAR(255) NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            applied_by VARCHAR(255) DEFAULT CURRENT_USER,
            execution_time_ms INTEGER,
            rollback_sql TEXT,
            description TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
        ON {self.migration_table} (version);
        
        CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at 
        ON {self.migration_table} (applied_at DESC);
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_table_sql)
                logger.info(f"Migration table '{self.migration_table}' ready")
    
    def get_file_checksum(self, filepath: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def get_applied_migrations(self) -> Dict[str, Dict]:
        """Get list of already applied migrations"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT version, filename, checksum, applied_at, description
                    FROM {self.migration_table}
                    ORDER BY version
                """)
                
                migrations = {}
                for row in cursor.fetchall():
                    migrations[row[0]] = {
                        'filename': row[1],
                        'checksum': row[2],
                        'applied_at': row[3],
                        'description': row[4]
                    }
                return migrations
    
    def get_migration_files(self) -> List[Tuple[str, Path]]:
        """Get sorted list of migration files"""
        if not self.schema_dir.exists():
            logger.error(f"Schema directory {self.schema_dir} does not exist")
            return []
        
        migration_files = []
        for file_path in sorted(self.schema_dir.glob("*.sql")):
            # Extract version from filename (e.g., "001_initial_schema.sql" -> "001")
            version = file_path.stem.split('_')[0]
            migration_files.append((version, file_path))
        
        return migration_files
    
    def validate_migration_integrity(self) -> bool:
        """Validate that applied migrations haven't been modified"""
        applied_migrations = self.get_applied_migrations()
        migration_files = dict(self.get_migration_files())
        
        integrity_ok = True
        
        for version, migration_info in applied_migrations.items():
            if version not in migration_files:
                logger.error(f"Applied migration {version} file not found")
                integrity_ok = False
                continue
            
            current_checksum = self.get_file_checksum(migration_files[version])
            if current_checksum != migration_info['checksum']:
                logger.error(f"Migration {version} has been modified after application")
                logger.error(f"Expected: {migration_info['checksum']}")
                logger.error(f"Current:  {current_checksum}")
                integrity_ok = False
        
        return integrity_ok
    
    def extract_rollback_sql(self, sql_content: str) -> Optional[str]:
        """Extract rollback SQL from migration file comments"""
        lines = sql_content.split('\n')
        rollback_lines = []
        in_rollback_section = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('-- ROLLBACK:'):
                in_rollback_section = True
                continue
            elif line.startswith('-- END ROLLBACK') or (line.startswith('--') and not in_rollback_section):
                if in_rollback_section:
                    break
            elif in_rollback_section and line.startswith('-- '):
                rollback_lines.append(line[3:])  # Remove '-- ' prefix
        
        return '\n'.join(rollback_lines) if rollback_lines else None
    
    def apply_migration(self, version: str, filepath: Path, dry_run: bool = False) -> bool:
        """Apply a single migration"""
        logger.info(f"Applying migration {version}: {filepath.name}")
        
        if not filepath.exists():
            logger.error(f"Migration file {filepath} not found")
            return False
        
        # Read and validate migration file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read migration file {filepath}: {e}")
            return False
        
        if not sql_content.strip():
            logger.warning(f"Migration file {filepath} is empty")
            return True
        
        checksum = self.get_file_checksum(filepath)
        rollback_sql = self.extract_rollback_sql(sql_content)
        
        if dry_run:
            logger.info(f"DRY RUN: Would apply migration {version}")
            logger.info(f"File: {filepath}")
            logger.info(f"Checksum: {checksum}")
            return True
        
        # Apply migration in transaction
        start_time = datetime.now()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Execute migration SQL
                    cursor.execute(sql_content)
                    
                    # Record migration
                    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    cursor.execute(f"""
                        INSERT INTO {self.migration_table} 
                        (version, filename, checksum, execution_time_ms, rollback_sql, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        version,
                        filepath.name,
                        checksum,
                        execution_time,
                        rollback_sql,
                        f"Applied migration {filepath.name}"
                    ))
                    
                    logger.info(f"Successfully applied migration {version} in {execution_time}ms")
                    return True
                    
        except psycopg2.Error as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            return False
    
    def rollback_migration(self, version: str, dry_run: bool = False) -> bool:
        """Rollback a specific migration"""
        logger.info(f"Rolling back migration {version}")
        
        # Get migration info
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT rollback_sql, filename 
                    FROM {self.migration_table} 
                    WHERE version = %s
                """, (version,))
                
                result = cursor.fetchone()
                if not result:
                    logger.error(f"Migration {version} not found in applied migrations")
                    return False
                
                rollback_sql, filename = result
                
                if not rollback_sql:
                    logger.error(f"No rollback SQL available for migration {version}")
                    return False
                
                if dry_run:
                    logger.info(f"DRY RUN: Would rollback migration {version}")
                    logger.info(f"Rollback SQL: {rollback_sql[:200]}...")
                    return True
                
                try:
                    # Execute rollback
                    cursor.execute(rollback_sql)
                    
                    # Remove migration record
                    cursor.execute(f"""
                        DELETE FROM {self.migration_table} 
                        WHERE version = %s
                    """, (version,))
                    
                    logger.info(f"Successfully rolled back migration {version}")
                    return True
                    
                except psycopg2.Error as e:
                    logger.error(f"Failed to rollback migration {version}: {e}")
                    return False
    
    def migrate_to_latest(self, dry_run: bool = False) -> bool:
        """Apply all pending migrations"""
        logger.info("Starting migration to latest version")
        
        # Ensure migration table exists
        if not dry_run:
            self.ensure_migration_table()
        
        # Validate existing migrations
        if not self.validate_migration_integrity():
            logger.error("Migration integrity check failed")
            return False
        
        # Get pending migrations
        applied_migrations = set(self.get_applied_migrations().keys())
        all_migrations = self.get_migration_files()
        
        pending_migrations = [
            (version, filepath) for version, filepath in all_migrations
            if version not in applied_migrations
        ]
        
        if not pending_migrations:
            logger.info("No pending migrations")
            return True
        
        logger.info(f"Found {len(pending_migrations)} pending migrations")
        
        # Apply pending migrations
        success_count = 0
        for version, filepath in pending_migrations:
            if self.apply_migration(version, filepath, dry_run):
                success_count += 1
            else:
                logger.error(f"Migration failed at version {version}")
                return False
        
        logger.info(f"Successfully applied {success_count} migrations")
        return True
    
    def get_migration_status(self) -> Dict:
        """Get current migration status"""
        applied_migrations = self.get_applied_migrations()
        all_migrations = dict(self.get_migration_files())
        
        status = {
            'total_migrations': len(all_migrations),
            'applied_migrations': len(applied_migrations),
            'pending_migrations': len(all_migrations) - len(applied_migrations),
            'latest_applied': None,
            'pending_list': [],
            'applied_list': list(applied_migrations.keys())
        }
        
        if applied_migrations:
            latest_version = max(applied_migrations.keys())
            status['latest_applied'] = {
                'version': latest_version,
                'applied_at': applied_migrations[latest_version]['applied_at'],
                'filename': applied_migrations[latest_version]['filename']
            }
        
        # Get pending migrations
        applied_set = set(applied_migrations.keys())
        status['pending_list'] = [
            version for version in all_migrations.keys()
            if version not in applied_set
        ]
        
        return status

def load_config(config_file: str = "database/config/database.yaml") -> Dict:
    """Load database configuration from YAML file"""
    config_path = Path(config_file)
    if not config_path.exists():
        # Return default configuration
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'workflow_db'),
            'username': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'ssl_mode': os.getenv('DB_SSL_MODE', 'prefer')
        }
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        sys.exit(1)

def build_connection_string(config: Dict) -> str:
    """Build PostgreSQL connection string from config"""
    return (
        f"host={config['host']} "
        f"port={config['port']} "
        f"dbname={config['database']} "
        f"user={config['username']} "
        f"password={config['password']} "
        f"sslmode={config.get('ssl_mode', 'prefer')}"
    )

def main():
    """Main migration CLI"""
    parser = argparse.ArgumentParser(description="Database Migration Tool")
    parser.add_argument('command', choices=['migrate', 'rollback', 'status', 'validate'],
                       help='Migration command to execute')
    parser.add_argument('--version', help='Specific version for rollback')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--config', default='database/config/database.yaml', help='Database config file')
    parser.add_argument('--schema-dir', default='database/schema', help='Schema directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    connection_string = build_connection_string(config)
    
    # Initialize migrator
    migrator = DatabaseMigrator(connection_string, args.schema_dir)
    
    try:
        if args.command == 'migrate':
            success = migrator.migrate_to_latest(args.dry_run)
            sys.exit(0 if success else 1)
            
        elif args.command == 'rollback':
            if not args.version:
                logger.error("Version required for rollback")
                sys.exit(1)
            success = migrator.rollback_migration(args.version, args.dry_run)
            sys.exit(0 if success else 1)
            
        elif args.command == 'status':
            status = migrator.get_migration_status()
            print(f"Migration Status:")
            print(f"  Total migrations: {status['total_migrations']}")
            print(f"  Applied: {status['applied_migrations']}")
            print(f"  Pending: {status['pending_migrations']}")
            
            if status['latest_applied']:
                print(f"  Latest applied: {status['latest_applied']['version']} "
                      f"({status['latest_applied']['applied_at']})")
            
            if status['pending_list']:
                print(f"  Pending migrations: {', '.join(status['pending_list'])}")
            
        elif args.command == 'validate':
            if migrator.validate_migration_integrity():
                print("Migration integrity check passed")
                sys.exit(0)
            else:
                print("Migration integrity check failed")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

