#!/usr/bin/env node

import { config } from 'dotenv';
import { DatabaseClient } from './database-client.js';
import { EnhancedTaskManagerMCPServer } from './mcp-server.js';
import { logger } from './utils/logger.js';

// Load environment variables
config();

async function main() {
  try {
    // Validate required environment variables
    const requiredEnvVars = [
      'DATABASE_HOST',
      'DATABASE_PORT',
      'DATABASE_NAME',
      'DATABASE_USER',
      'DATABASE_PASSWORD',
      'CODEGEN_API_URL',
      'CODEGEN_API_KEY',
      'CLAUDE_CODE_API_URL',
      'CLAUDE_CODE_API_KEY'
    ];

    const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);
    if (missingVars.length > 0) {
      throw new Error(`Missing required environment variables: ${missingVars.join(', ')}`);
    }

    // Initialize database client
    const dbConfig = {
      host: process.env.DATABASE_HOST!,
      port: parseInt(process.env.DATABASE_PORT!),
      database: process.env.DATABASE_NAME!,
      user: process.env.DATABASE_USER!,
      password: process.env.DATABASE_PASSWORD!,
      ssl: process.env.DATABASE_SSL === 'true',
      max: parseInt(process.env.DATABASE_MAX_CONNECTIONS || '20'),
      idleTimeoutMillis: parseInt(process.env.DATABASE_IDLE_TIMEOUT || '30000'),
      connectionTimeoutMillis: parseInt(process.env.DATABASE_CONNECTION_TIMEOUT || '2000')
    };

    const db = new DatabaseClient(dbConfig);
    await db.connect();

    // Initialize workflow configuration
    const workflowConfig = {
      codegenApiUrl: process.env.CODEGEN_API_URL!,
      codegenApiKey: process.env.CODEGEN_API_KEY!,
      claudeCodeApiUrl: process.env.CLAUDE_CODE_API_URL!,
      claudeCodeApiKey: process.env.CLAUDE_CODE_API_KEY!
    };

    // Initialize MCP server
    const server = new EnhancedTaskManagerMCPServer(db, workflowConfig);

    // Handle graceful shutdown
    const shutdown = async (signal: string) => {
      logger.info(`Received ${signal}, shutting down gracefully...`);
      try {
        await server.stop();
        process.exit(0);
      } catch (error) {
        logger.error('Error during shutdown:', error);
        process.exit(1);
      }
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));

    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
      logger.error('Uncaught exception:', error);
      process.exit(1);
    });

    process.on('unhandledRejection', (reason, promise) => {
      logger.error('Unhandled rejection at:', promise, 'reason:', reason);
      process.exit(1);
    });

    // Start the server
    await server.start();
    logger.info('Enhanced Task Manager MCP Server is running');

  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Run the server
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    logger.error('Fatal error:', error);
    process.exit(1);
  });
}

