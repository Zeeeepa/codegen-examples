import { z } from 'zod';

export const ServerConfigSchema = z.object({
  database: z.object({
    host: z.string(),
    port: z.number().min(1).max(65535),
    database: z.string(),
    user: z.string(),
    password: z.string(),
    ssl: z.boolean().default(false),
    maxConnections: z.number().default(20),
    idleTimeoutMs: z.number().default(30000),
    connectionTimeoutMs: z.number().default(2000)
  }),
  workflows: z.object({
    codegen: z.object({
      apiUrl: z.string().url(),
      apiKey: z.string(),
      defaultTimeout: z.number().default(30)
    }),
    claudeCode: z.object({
      apiUrl: z.string().url(),
      apiKey: z.string(),
      defaultTimeout: z.number().default(5)
    })
  }),
  server: z.object({
    logLevel: z.enum(['error', 'warn', 'info', 'debug']).default('info'),
    enableMetrics: z.boolean().default(true),
    metricsPort: z.number().default(9090),
    healthCheckInterval: z.number().default(30000)
  }),
  features: z.object({
    autoParseNaturalLanguage: z.boolean().default(true),
    enableWorkflowTriggers: z.boolean().default(true),
    enableDependencyAnalysis: z.boolean().default(true),
    enableScheduledTasks: z.boolean().default(true),
    maxTasksPerProject: z.number().default(10000),
    maxDependenciesPerTask: z.number().default(50)
  })
});

export type ServerConfig = z.infer<typeof ServerConfigSchema>;

export const defaultConfig: ServerConfig = {
  database: {
    host: 'localhost',
    port: 5432,
    database: 'task_manager',
    user: 'task_manager_user',
    password: '',
    ssl: false,
    maxConnections: 20,
    idleTimeoutMs: 30000,
    connectionTimeoutMs: 2000
  },
  workflows: {
    codegen: {
      apiUrl: 'https://api.codegen.sh',
      apiKey: '',
      defaultTimeout: 30
    },
    claudeCode: {
      apiUrl: 'https://api.claude-code.com',
      apiKey: '',
      defaultTimeout: 5
    }
  },
  server: {
    logLevel: 'info',
    enableMetrics: true,
    metricsPort: 9090,
    healthCheckInterval: 30000
  },
  features: {
    autoParseNaturalLanguage: true,
    enableWorkflowTriggers: true,
    enableDependencyAnalysis: true,
    enableScheduledTasks: true,
    maxTasksPerProject: 10000,
    maxDependenciesPerTask: 50
  }
};

export function loadConfig(): ServerConfig {
  const config = { ...defaultConfig };

  // Override with environment variables
  if (process.env.DATABASE_HOST) config.database.host = process.env.DATABASE_HOST;
  if (process.env.DATABASE_PORT) config.database.port = parseInt(process.env.DATABASE_PORT);
  if (process.env.DATABASE_NAME) config.database.database = process.env.DATABASE_NAME;
  if (process.env.DATABASE_USER) config.database.user = process.env.DATABASE_USER;
  if (process.env.DATABASE_PASSWORD) config.database.password = process.env.DATABASE_PASSWORD;
  if (process.env.DATABASE_SSL) config.database.ssl = process.env.DATABASE_SSL === 'true';

  if (process.env.CODEGEN_API_URL) config.workflows.codegen.apiUrl = process.env.CODEGEN_API_URL;
  if (process.env.CODEGEN_API_KEY) config.workflows.codegen.apiKey = process.env.CODEGEN_API_KEY;
  if (process.env.CLAUDE_CODE_API_URL) config.workflows.claudeCode.apiUrl = process.env.CLAUDE_CODE_API_URL;
  if (process.env.CLAUDE_CODE_API_KEY) config.workflows.claudeCode.apiKey = process.env.CLAUDE_CODE_API_KEY;

  if (process.env.LOG_LEVEL) {
    config.server.logLevel = process.env.LOG_LEVEL as 'error' | 'warn' | 'info' | 'debug';
  }

  return ServerConfigSchema.parse(config);
}

