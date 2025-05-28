#!/usr/bin/env python3
"""
Database Rollback System for AI-Powered Development Workflow
Handles safe rollback operations with dependency checking and data preservation
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rollback.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseRollback:
    """Handles safe database rollback operations with dependency checking"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.migration_table = "schema_migrations"
        self.backup_table = "rollback_backups"
        
    def get_connection(self) -> psycopg2.extensions.connection:
        """Get database connection"""
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def ensure_backup_table(self) -> None:
        """Create backup tracking table if it doesn't exist"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.backup_table} (
            id SERIAL PRIMARY KEY,
            backup_name VARCHAR(255) NOT NULL UNIQUE,
            migration_version VARCHAR(50) NOT NULL,
            table_name VARCHAR(255) NOT NULL,
            backup_data JSONB,
            row_count INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_by VARCHAR(255) DEFAULT CURRENT_USER,
            description TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_rollback_backups_version 
        ON {self.backup_table} (migration_version);
        
        CREATE INDEX IF NOT EXISTS idx_rollback_backups_created_at 
        ON {self.backup_table} (created_at DESC);
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_table_sql)
                logger.info(f"Backup table '{self.backup_table}' ready")
    
    def get_migration_dependencies(self, version: str) -> List[str]:
        """Get migrations that depend on the specified version"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get all migrations applied after this version
                cursor.execute(f"""
                    SELECT version, filename 
                    FROM {self.migration_table} 
                    WHERE version > %s 
                    ORDER BY version DESC
                """, (version,))
                
                return [row[0] for row in cursor.fetchall()]
    
    def analyze_data_impact(self, version: str) -> Dict:
        """Analyze potential data loss from rollback"""
        impact_analysis = {
            'tables_affected': [],
            'estimated_data_loss': {},
            'foreign_key_constraints': [],
            'indexes_dropped': [],
            'functions_dropped': []
        }
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get rollback SQL for analysis
                cursor.execute(f"""
                    SELECT rollback_sql 
                    FROM {self.migration_table} 
                    WHERE version = %s
                """, (version,))
                
                result = cursor.fetchone()
                if not result or not result[0]:
                    return impact_analysis
                
                rollback_sql = result[0].upper()
                
                # Analyze DROP TABLE statements
                if 'DROP TABLE' in rollback_sql:
                    # Extract table names (simplified parsing)
                    lines = rollback_sql.split('\n')
                    for line in lines:
                        if 'DROP TABLE' in line:
                            # Extract table name (basic parsing)
                            parts = line.split()
                            if len(parts) >= 3:
                                table_name = parts[2].strip(';').strip('"')
                                impact_analysis['tables_affected'].append(table_name)
                                
                                # Get row count for impact assessment
                                try:
                                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                                    row_count = cursor.fetchone()[0]
                                    impact_analysis['estimated_data_loss'][table_name] = row_count
                                except psycopg2.Error:
                                    impact_analysis['estimated_data_loss'][table_name] = 'unknown'
                
                # Analyze other impacts
                if 'DROP INDEX' in rollback_sql:
                    impact_analysis['indexes_dropped'] = self._extract_dropped_objects(rollback_sql, 'DROP INDEX')
                
                if 'DROP FUNCTION' in rollback_sql:
                    impact_analysis['functions_dropped'] = self._extract_dropped_objects(rollback_sql, 'DROP FUNCTION')
        
        return impact_analysis
    
    def _extract_dropped_objects(self, sql: str, drop_type: str) -> List[str]:
        """Extract object names from DROP statements"""
        objects = []
        lines = sql.split('\n')
        for line in lines:
            if drop_type in line:
                parts = line.split()
                if len(parts) >= 3:
                    obj_name = parts[2].strip(';').strip('"')
                    objects.append(obj_name)
        return objects
    
    def create_data_backup(self, version: str, tables: List[str]) -> bool:
        """Create backup of data before rollback"""
        logger.info(f"Creating data backup for rollback of version {version}")
        
        self.ensure_backup_table()
        backup_name = f"rollback_{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for table_name in tables:
                    try:
                        # Get table data
                        cursor.execute(f"SELECT * FROM {table_name}")
                        rows = cursor.fetchall()
                        
                        # Get column names
                        cursor.execute(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = %s 
                            ORDER BY ordinal_position
                        """, (table_name,))
                        columns = [row[0] for row in cursor.fetchall()]
                        
                        # Convert to JSON-serializable format
                        backup_data = {
                            'columns': columns,
                            'rows': [dict(zip(columns, [str(val) for val in row])) for row in rows]
                        }
                        
                        # Store backup
                        cursor.execute(f"""
                            INSERT INTO {self.backup_table} 
                            (backup_name, migration_version, table_name, backup_data, row_count, description)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            f"{backup_name}_{table_name}",
                            version,
                            table_name,
                            json.dumps(backup_data),
                            len(rows),
                            f"Pre-rollback backup of {table_name} for migration {version}"
                        ))
                        
                        logger.info(f"Backed up {len(rows)} rows from {table_name}")
                        
                    except psycopg2.Error as e:
                        logger.error(f"Failed to backup table {table_name}: {e}")
                        return False
        
        logger.info(f"Data backup completed: {backup_name}")
        return True
    
    def restore_data_backup(self, backup_name: str) -> bool:
        """Restore data from backup"""
        logger.info(f"Restoring data from backup: {backup_name}")
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get backup data
                cursor.execute(f"""
                    SELECT table_name, backup_data 
                    FROM {self.backup_table} 
                    WHERE backup_name LIKE %s
                """, (f"{backup_name}%",))
                
                backups = cursor.fetchall()
                if not backups:
                    logger.error(f"No backup found with name: {backup_name}")
                    return False
                
                for table_name, backup_data_json in backups:
                    try:
                        backup_data = json.loads(backup_data_json)
                        columns = backup_data['columns']
                        rows = backup_data['rows']
                        
                        # Clear existing data
                        cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                        
                        # Restore data
                        if rows:
                            placeholders = ', '.join(['%s'] * len(columns))
                            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                            
                            for row_dict in rows:
                                values = [row_dict[col] for col in columns]
                                cursor.execute(insert_sql, values)
                        
                        logger.info(f"Restored {len(rows)} rows to {table_name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to restore table {table_name}: {e}")
                        return False
        
        logger.info("Data restoration completed")
        return True
    
    def safe_rollback(self, target_version: str, force: bool = False, backup_data: bool = True) -> bool:
        """Perform safe rollback with dependency checking and data backup"""
        logger.info(f"Starting safe rollback to version {target_version}")
        
        # Check if target version exists
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT version, rollback_sql 
                    FROM {self.migration_table} 
                    WHERE version = %s
                """, (target_version,))
                
                result = cursor.fetchone()
                if not result:
                    logger.error(f"Migration version {target_version} not found")
                    return False
                
                if not result[1]:
                    logger.error(f"No rollback SQL available for version {target_version}")
                    return False
        
        # Get dependent migrations
        dependent_versions = self.get_migration_dependencies(target_version)
        if dependent_versions and not force:
            logger.error(f"Cannot rollback version {target_version} - dependent migrations exist:")
            for dep_version in dependent_versions:
                logger.error(f"  - {dep_version}")
            logger.error("Use --force to rollback anyway (will rollback all dependent migrations)")
            return False
        
        # Analyze data impact
        impact = self.analyze_data_impact(target_version)
        if impact['tables_affected']:
            logger.warning("Rollback will affect the following tables:")
            for table in impact['tables_affected']:
                row_count = impact['estimated_data_loss'].get(table, 'unknown')
                logger.warning(f"  - {table}: {row_count} rows")
            
            if not force:
                response = input("Continue with rollback? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Rollback cancelled by user")
                    return False
        
        # Create data backup if requested
        if backup_data and impact['tables_affected']:
            if not self.create_data_backup(target_version, impact['tables_affected']):
                logger.error("Failed to create data backup")
                if not force:
                    return False
        
        # Perform rollback (including dependent migrations if force=True)
        versions_to_rollback = [target_version]
        if force and dependent_versions:
            versions_to_rollback = dependent_versions + [target_version]
        
        success = True
        for version in versions_to_rollback:
            if not self._execute_single_rollback(version):
                success = False
                break
        
        if success:
            logger.info(f"Successfully rolled back to version {target_version}")
        else:
            logger.error("Rollback failed - database may be in inconsistent state")
        
        return success
    
    def _execute_single_rollback(self, version: str) -> bool:
        """Execute rollback for a single migration"""
        logger.info(f"Rolling back migration {version}")
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Get rollback SQL
                    cursor.execute(f"""
                        SELECT rollback_sql 
                        FROM {self.migration_table} 
                        WHERE version = %s
                    """, (version,))
                    
                    result = cursor.fetchone()
                    if not result or not result[0]:
                        logger.error(f"No rollback SQL for version {version}")
                        return False
                    
                    rollback_sql = result[0]
                    
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
    
    def list_backups(self) -> List[Dict]:
        """List available data backups"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT DISTINCT backup_name, migration_version, created_at, created_by,
                           COUNT(*) as table_count, SUM(row_count) as total_rows
                    FROM {self.backup_table}
                    GROUP BY backup_name, migration_version, created_at, created_by
                    ORDER BY created_at DESC
                """)
                
                backups = []
                for row in cursor.fetchall():
                    backups.append({
                        'backup_name': row[0],
                        'migration_version': row[1],
                        'created_at': row[2],
                        'created_by': row[3],
                        'table_count': row[4],
                        'total_rows': row[5]
                    })
                
                return backups
    
    def cleanup_old_backups(self, days_old: int = 30) -> int:
        """Clean up old backup data"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    DELETE FROM {self.backup_table} 
                    WHERE created_at < %s
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} old backup records")
                return deleted_count

def load_config(config_file: str = "database/config/database.yaml") -> Dict:
    """Load database configuration"""
    config_path = Path(config_file)
    if not config_path.exists():
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'workflow_db'),
            'username': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'ssl_mode': os.getenv('DB_SSL_MODE', 'prefer')
        }
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def build_connection_string(config: Dict) -> str:
    """Build PostgreSQL connection string"""
    return (
        f"host={config['host']} "
        f"port={config['port']} "
        f"dbname={config['database']} "
        f"user={config['username']} "
        f"password={config['password']} "
        f"sslmode={config.get('ssl_mode', 'prefer')}"
    )

def main():
    """Main rollback CLI"""
    parser = argparse.ArgumentParser(description="Database Rollback Tool")
    parser.add_argument('command', choices=['rollback', 'list-backups', 'restore-backup', 'cleanup-backups'],
                       help='Rollback command to execute')
    parser.add_argument('--version', help='Migration version to rollback to')
    parser.add_argument('--backup-name', help='Backup name to restore')
    parser.add_argument('--force', action='store_true', help='Force rollback even with dependencies')
    parser.add_argument('--no-backup', action='store_true', help='Skip data backup before rollback')
    parser.add_argument('--cleanup-days', type=int, default=30, help='Days old for backup cleanup')
    parser.add_argument('--config', default='database/config/database.yaml', help='Database config file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    connection_string = build_connection_string(config)
    
    # Initialize rollback system
    rollback_system = DatabaseRollback(connection_string)
    
    try:
        if args.command == 'rollback':
            if not args.version:
                logger.error("Version required for rollback")
                sys.exit(1)
            
            success = rollback_system.safe_rollback(
                args.version, 
                force=args.force, 
                backup_data=not args.no_backup
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'list-backups':
            backups = rollback_system.list_backups()
            if not backups:
                print("No backups found")
            else:
                print("Available backups:")
                for backup in backups:
                    print(f"  {backup['backup_name']}")
                    print(f"    Version: {backup['migration_version']}")
                    print(f"    Created: {backup['created_at']} by {backup['created_by']}")
                    print(f"    Tables: {backup['table_count']}, Rows: {backup['total_rows']}")
                    print()
            
        elif args.command == 'restore-backup':
            if not args.backup_name:
                logger.error("Backup name required for restore")
                sys.exit(1)
            
            success = rollback_system.restore_data_backup(args.backup_name)
            sys.exit(0 if success else 1)
            
        elif args.command == 'cleanup-backups':
            deleted_count = rollback_system.cleanup_old_backups(args.cleanup_days)
            print(f"Cleaned up {deleted_count} old backup records")
            
    except Exception as e:
        logger.error(f"Rollback operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

