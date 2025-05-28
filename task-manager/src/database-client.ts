import { Pool, PoolClient, QueryResult } from 'pg';
import { z } from 'zod';
import { logger } from './utils/logger.js';

// Zod schemas for type safety
export const TaskStatus = z.enum(['pending', 'in_progress', 'blocked', 'review', 'completed', 'cancelled', 'failed']);
export const TaskPriority = z.enum(['low', 'medium', 'high', 'critical']);
export const TaskComplexity = z.enum(['simple', 'moderate', 'complex', 'epic']);
export const WorkflowTriggerType = z.enum(['codegen', 'claude_code', 'webhook', 'manual', 'scheduled']);

export const ProjectSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().optional(),
  repository_url: z.string().url().optional(),
  branch_name: z.string().default('main'),
  created_at: z.date(),
  updated_at: z.date(),
  metadata: z.record(z.any()).default({})
});

export const TaskSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid().optional(),
  title: z.string(),
  description: z.string().optional(),
  natural_language_input: z.string().optional(),
  parsed_requirements: z.record(z.any()).optional(),
  status: TaskStatus.default('pending'),
  priority: TaskPriority.default('medium'),
  complexity: TaskComplexity.default('moderate'),
  estimated_hours: z.number().optional(),
  actual_hours: z.number().optional(),
  assignee: z.string().optional(),
  tags: z.array(z.string()).default([]),
  created_at: z.date(),
  updated_at: z.date(),
  due_date: z.date().optional(),
  completed_at: z.date().optional(),
  metadata: z.record(z.any()).default({})
});

export const TaskDependencySchema = z.object({
  id: z.string().uuid(),
  task_id: z.string().uuid(),
  depends_on_task_id: z.string().uuid(),
  dependency_type: z.string().default('blocks'),
  created_at: z.date()
});

export const WorkflowTriggerSchema = z.object({
  id: z.string().uuid(),
  task_id: z.string().uuid(),
  trigger_type: WorkflowTriggerType,
  trigger_config: z.record(z.any()),
  status: z.string().default('pending'),
  triggered_at: z.date().optional(),
  completed_at: z.date().optional(),
  result: z.record(z.any()).optional(),
  error_message: z.string().optional(),
  retry_count: z.number().default(0),
  max_retries: z.number().default(3),
  created_at: z.date(),
  updated_at: z.date()
});

export type Project = z.infer<typeof ProjectSchema>;
export type Task = z.infer<typeof TaskSchema>;
export type TaskDependency = z.infer<typeof TaskDependencySchema>;
export type WorkflowTrigger = z.infer<typeof WorkflowTriggerSchema>;

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
  ssl?: boolean;
  max?: number;
  idleTimeoutMillis?: number;
  connectionTimeoutMillis?: number;
}

export class DatabaseClient {
  private pool: Pool;
  private isConnected = false;

  constructor(config: DatabaseConfig) {
    this.pool = new Pool({
      host: config.host,
      port: config.port,
      database: config.database,
      user: config.user,
      password: config.password,
      ssl: config.ssl ? { rejectUnauthorized: false } : false,
      max: config.max || 20,
      idleTimeoutMillis: config.idleTimeoutMillis || 30000,
      connectionTimeoutMillis: config.connectionTimeoutMillis || 2000,
    });

    this.pool.on('error', (err) => {
      logger.error('Unexpected error on idle client', err);
    });
  }

  async connect(): Promise<void> {
    try {
      const client = await this.pool.connect();
      client.release();
      this.isConnected = true;
      logger.info('Database connected successfully');
    } catch (error) {
      logger.error('Failed to connect to database:', error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    await this.pool.end();
    this.isConnected = false;
    logger.info('Database disconnected');
  }

  async query<T = any>(text: string, params?: any[]): Promise<QueryResult<T>> {
    const start = Date.now();
    try {
      const result = await this.pool.query(text, params);
      const duration = Date.now() - start;
      logger.debug('Executed query', { text, duration, rows: result.rowCount });
      return result;
    } catch (error) {
      logger.error('Query error', { text, params, error });
      throw error;
    }
  }

  async transaction<T>(callback: (client: PoolClient) => Promise<T>): Promise<T> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // Project operations
  async createProject(project: Omit<Project, 'id' | 'created_at' | 'updated_at'>): Promise<Project> {
    const query = `
      INSERT INTO projects (name, description, repository_url, branch_name, metadata)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING *
    `;
    const values = [
      project.name,
      project.description,
      project.repository_url,
      project.branch_name,
      JSON.stringify(project.metadata)
    ];
    
    const result = await this.query<Project>(query, values);
    return ProjectSchema.parse(result.rows[0]);
  }

  async getProject(id: string): Promise<Project | null> {
    const query = 'SELECT * FROM projects WHERE id = $1';
    const result = await this.query<Project>(query, [id]);
    return result.rows.length > 0 ? ProjectSchema.parse(result.rows[0]) : null;
  }

  async listProjects(): Promise<Project[]> {
    const query = 'SELECT * FROM projects ORDER BY created_at DESC';
    const result = await this.query<Project>(query);
    return result.rows.map(row => ProjectSchema.parse(row));
  }

  // Task operations
  async createTask(task: Omit<Task, 'id' | 'created_at' | 'updated_at'>): Promise<Task> {
    const query = `
      INSERT INTO tasks (
        project_id, title, description, natural_language_input, parsed_requirements,
        status, priority, complexity, estimated_hours, assignee, tags, due_date, metadata
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
      RETURNING *
    `;
    const values = [
      task.project_id,
      task.title,
      task.description,
      task.natural_language_input,
      task.parsed_requirements ? JSON.stringify(task.parsed_requirements) : null,
      task.status,
      task.priority,
      task.complexity,
      task.estimated_hours,
      task.assignee,
      task.tags,
      task.due_date,
      JSON.stringify(task.metadata)
    ];
    
    const result = await this.query<Task>(query, values);
    return TaskSchema.parse(result.rows[0]);
  }

  async getTask(id: string): Promise<Task | null> {
    const query = 'SELECT * FROM tasks WHERE id = $1';
    const result = await this.query<Task>(query, [id]);
    return result.rows.length > 0 ? TaskSchema.parse(result.rows[0]) : null;
  }

  async updateTask(id: string, updates: Partial<Omit<Task, 'id' | 'created_at' | 'updated_at'>>): Promise<Task> {
    const setClause = Object.keys(updates)
      .map((key, index) => `${key} = $${index + 2}`)
      .join(', ');
    
    const query = `
      UPDATE tasks 
      SET ${setClause}
      WHERE id = $1
      RETURNING *
    `;
    
    const values = [id, ...Object.values(updates)];
    const result = await this.query<Task>(query, values);
    
    if (result.rows.length === 0) {
      throw new Error(`Task with id ${id} not found`);
    }
    
    return TaskSchema.parse(result.rows[0]);
  }

  async listTasks(filters?: {
    project_id?: string;
    status?: string;
    priority?: string;
    assignee?: string;
    limit?: number;
    offset?: number;
  }): Promise<Task[]> {
    let query = 'SELECT * FROM tasks WHERE 1=1';
    const values: any[] = [];
    let paramIndex = 1;

    if (filters?.project_id) {
      query += ` AND project_id = $${paramIndex++}`;
      values.push(filters.project_id);
    }

    if (filters?.status) {
      query += ` AND status = $${paramIndex++}`;
      values.push(filters.status);
    }

    if (filters?.priority) {
      query += ` AND priority = $${paramIndex++}`;
      values.push(filters.priority);
    }

    if (filters?.assignee) {
      query += ` AND assignee = $${paramIndex++}`;
      values.push(filters.assignee);
    }

    query += ' ORDER BY created_at DESC';

    if (filters?.limit) {
      query += ` LIMIT $${paramIndex++}`;
      values.push(filters.limit);
    }

    if (filters?.offset) {
      query += ` OFFSET $${paramIndex++}`;
      values.push(filters.offset);
    }

    const result = await this.query<Task>(query, values);
    return result.rows.map(row => TaskSchema.parse(row));
  }

  async searchTasks(searchTerm: string, limit = 10): Promise<Task[]> {
    const query = `
      SELECT *, ts_rank(search_vector, plainto_tsquery('english', $1)) as rank
      FROM tasks
      WHERE search_vector @@ plainto_tsquery('english', $1)
      ORDER BY rank DESC, created_at DESC
      LIMIT $2
    `;
    
    const result = await this.query<Task>(query, [searchTerm, limit]);
    return result.rows.map(row => TaskSchema.parse(row));
  }

  // Dependency operations
  async addTaskDependency(taskId: string, dependsOnTaskId: string, dependencyType = 'blocks'): Promise<TaskDependency> {
    const query = `
      INSERT INTO task_dependencies (task_id, depends_on_task_id, dependency_type)
      VALUES ($1, $2, $3)
      RETURNING *
    `;
    
    const result = await this.query<TaskDependency>(query, [taskId, dependsOnTaskId, dependencyType]);
    return TaskDependencySchema.parse(result.rows[0]);
  }

  async removeTaskDependency(taskId: string, dependsOnTaskId: string): Promise<void> {
    const query = 'DELETE FROM task_dependencies WHERE task_id = $1 AND depends_on_task_id = $2';
    await this.query(query, [taskId, dependsOnTaskId]);
  }

  async getTaskDependencies(taskId: string): Promise<TaskDependency[]> {
    const query = 'SELECT * FROM task_dependencies WHERE task_id = $1';
    const result = await this.query<TaskDependency>(query, [taskId]);
    return result.rows.map(row => TaskDependencySchema.parse(row));
  }

  async getDependencyGraph(projectId?: string): Promise<{ nodes: Task[], edges: TaskDependency[] }> {
    let taskQuery = 'SELECT * FROM tasks';
    let depQuery = `
      SELECT td.* FROM task_dependencies td
      JOIN tasks t1 ON td.task_id = t1.id
      JOIN tasks t2 ON td.depends_on_task_id = t2.id
    `;
    
    const values: any[] = [];
    
    if (projectId) {
      taskQuery += ' WHERE project_id = $1';
      depQuery += ' WHERE t1.project_id = $1 AND t2.project_id = $1';
      values.push(projectId);
    }

    const [tasksResult, depsResult] = await Promise.all([
      this.query<Task>(taskQuery, values),
      this.query<TaskDependency>(depQuery, values)
    ]);

    return {
      nodes: tasksResult.rows.map(row => TaskSchema.parse(row)),
      edges: depsResult.rows.map(row => TaskDependencySchema.parse(row))
    };
  }

  // Workflow trigger operations
  async createWorkflowTrigger(trigger: Omit<WorkflowTrigger, 'id' | 'created_at' | 'updated_at'>): Promise<WorkflowTrigger> {
    const query = `
      INSERT INTO workflow_triggers (
        task_id, trigger_type, trigger_config, status, max_retries
      )
      VALUES ($1, $2, $3, $4, $5)
      RETURNING *
    `;
    
    const values = [
      trigger.task_id,
      trigger.trigger_type,
      JSON.stringify(trigger.trigger_config),
      trigger.status,
      trigger.max_retries
    ];
    
    const result = await this.query<WorkflowTrigger>(query, values);
    return WorkflowTriggerSchema.parse(result.rows[0]);
  }

  async updateWorkflowTrigger(id: string, updates: Partial<WorkflowTrigger>): Promise<WorkflowTrigger> {
    const setClause = Object.keys(updates)
      .map((key, index) => `${key} = $${index + 2}`)
      .join(', ');
    
    const query = `
      UPDATE workflow_triggers 
      SET ${setClause}
      WHERE id = $1
      RETURNING *
    `;
    
    const values = [id, ...Object.values(updates)];
    const result = await this.query<WorkflowTrigger>(query, values);
    
    if (result.rows.length === 0) {
      throw new Error(`Workflow trigger with id ${id} not found`);
    }
    
    return WorkflowTriggerSchema.parse(result.rows[0]);
  }

  async getPendingWorkflowTriggers(): Promise<WorkflowTrigger[]> {
    const query = 'SELECT * FROM workflow_triggers WHERE status = $1 ORDER BY created_at ASC';
    const result = await this.query<WorkflowTrigger>(query, ['pending']);
    return result.rows.map(row => WorkflowTriggerSchema.parse(row));
  }

  // Analytics and reporting
  async getTaskStatistics(projectId?: string): Promise<{
    total: number;
    by_status: Record<string, number>;
    by_priority: Record<string, number>;
    by_complexity: Record<string, number>;
    avg_completion_time: number | null;
  }> {
    let whereClause = '';
    const values: any[] = [];
    
    if (projectId) {
      whereClause = 'WHERE project_id = $1';
      values.push(projectId);
    }

    const queries = [
      `SELECT COUNT(*) as total FROM tasks ${whereClause}`,
      `SELECT status, COUNT(*) as count FROM tasks ${whereClause} GROUP BY status`,
      `SELECT priority, COUNT(*) as count FROM tasks ${whereClause} GROUP BY priority`,
      `SELECT complexity, COUNT(*) as count FROM tasks ${whereClause} GROUP BY complexity`,
      `SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/3600) as avg_hours 
       FROM tasks ${whereClause} AND completed_at IS NOT NULL`
    ];

    const results = await Promise.all(
      queries.map(query => this.query(query, values))
    );

    const byStatus: Record<string, number> = {};
    const byPriority: Record<string, number> = {};
    const byComplexity: Record<string, number> = {};

    results[1].rows.forEach(row => byStatus[row.status] = parseInt(row.count));
    results[2].rows.forEach(row => byPriority[row.priority] = parseInt(row.count));
    results[3].rows.forEach(row => byComplexity[row.complexity] = parseInt(row.count));

    return {
      total: parseInt(results[0].rows[0].total),
      by_status: byStatus,
      by_priority: byPriority,
      by_complexity: byComplexity,
      avg_completion_time: results[4].rows[0].avg_hours ? parseFloat(results[4].rows[0].avg_hours) : null
    };
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.query('SELECT 1');
      return true;
    } catch (error) {
      logger.error('Database health check failed:', error);
      return false;
    }
  }
}

