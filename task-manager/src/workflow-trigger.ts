import axios from 'axios';
import { CronJob } from 'cron';
import { z } from 'zod';
import { logger } from './utils/logger.js';
import { DatabaseClient, WorkflowTrigger, Task } from './database-client.js';

// Configuration schemas
export const CodegenTriggerConfigSchema = z.object({
  auto_trigger: z.boolean().default(false),
  review_required: z.boolean().default(true),
  repository_url: z.string().url().optional(),
  branch_name: z.string().default('main'),
  target_files: z.array(z.string()).default([]),
  agent_instructions: z.string().optional(),
  timeout_minutes: z.number().default(30)
});

export const ClaudeCodeTriggerConfigSchema = z.object({
  validation_type: z.enum(['syntax', 'logic', 'full']).default('full'),
  auto_fix: z.boolean().default(false),
  test_coverage_required: z.boolean().default(true),
  security_scan: z.boolean().default(true),
  performance_check: z.boolean().default(false)
});

export const WebhookTriggerConfigSchema = z.object({
  endpoint: z.string().url(),
  method: z.enum(['GET', 'POST', 'PUT', 'PATCH']).default('POST'),
  headers: z.record(z.string()).default({}),
  payload_template: z.string().optional(),
  authentication: z.object({
    type: z.enum(['none', 'bearer', 'basic', 'api_key']).default('none'),
    token: z.string().optional(),
    username: z.string().optional(),
    password: z.string().optional(),
    api_key_header: z.string().optional()
  }).optional()
});

export const ScheduledTriggerConfigSchema = z.object({
  cron_expression: z.string(),
  timezone: z.string().default('UTC'),
  max_executions: z.number().optional(),
  execution_count: z.number().default(0)
});

export const ManualTriggerConfigSchema = z.object({
  approval_required: z.boolean().default(true),
  approvers: z.array(z.string()).default([]),
  instructions: z.string().optional()
});

export type CodegenTriggerConfig = z.infer<typeof CodegenTriggerConfigSchema>;
export type ClaudeCodeTriggerConfig = z.infer<typeof ClaudeCodeTriggerConfigSchema>;
export type WebhookTriggerConfig = z.infer<typeof WebhookTriggerConfigSchema>;
export type ScheduledTriggerConfig = z.infer<typeof ScheduledTriggerConfigSchema>;
export type ManualTriggerConfig = z.infer<typeof ManualTriggerConfigSchema>;

export interface WorkflowTriggerResult {
  success: boolean;
  data?: any;
  error?: string;
  execution_time_ms: number;
  metadata?: Record<string, any>;
}

export class WorkflowTriggerManager {
  private db: DatabaseClient;
  private scheduledJobs: Map<string, CronJob> = new Map();
  private codegenApiUrl: string;
  private codegenApiKey: string;
  private claudeCodeApiUrl: string;
  private claudeCodeApiKey: string;

  constructor(
    db: DatabaseClient,
    config: {
      codegenApiUrl: string;
      codegenApiKey: string;
      claudeCodeApiUrl: string;
      claudeCodeApiKey: string;
    }
  ) {
    this.db = db;
    this.codegenApiUrl = config.codegenApiUrl;
    this.codegenApiKey = config.codegenApiKey;
    this.claudeCodeApiUrl = config.claudeCodeApiUrl;
    this.claudeCodeApiKey = config.claudeCodeApiKey;
  }

  /**
   * Process pending workflow triggers
   */
  async processPendingTriggers(): Promise<void> {
    logger.info('Processing pending workflow triggers');

    try {
      const pendingTriggers = await this.db.getPendingWorkflowTriggers();
      
      for (const trigger of pendingTriggers) {
        try {
          await this.executeTrigger(trigger);
        } catch (error) {
          logger.error('Failed to execute trigger', { 
            triggerId: trigger.id, 
            error 
          });
          
          // Update trigger with error
          await this.db.updateWorkflowTrigger(trigger.id, {
            status: 'failed',
            error_message: error instanceof Error ? error.message : 'Unknown error',
            retry_count: trigger.retry_count + 1
          });
        }
      }
    } catch (error) {
      logger.error('Failed to process pending triggers', { error });
    }
  }

  /**
   * Execute a specific workflow trigger
   */
  async executeTrigger(trigger: WorkflowTrigger): Promise<WorkflowTriggerResult> {
    const startTime = Date.now();
    logger.info('Executing workflow trigger', { 
      triggerId: trigger.id, 
      type: trigger.trigger_type 
    });

    try {
      // Mark trigger as triggered
      await this.db.updateWorkflowTrigger(trigger.id, {
        status: 'triggered',
        triggered_at: new Date()
      });

      let result: WorkflowTriggerResult;

      switch (trigger.trigger_type) {
        case 'codegen':
          result = await this.executeCodegenTrigger(trigger);
          break;
        case 'claude_code':
          result = await this.executeClaudeCodeTrigger(trigger);
          break;
        case 'webhook':
          result = await this.executeWebhookTrigger(trigger);
          break;
        case 'manual':
          result = await this.executeManualTrigger(trigger);
          break;
        case 'scheduled':
          result = await this.executeScheduledTrigger(trigger);
          break;
        default:
          throw new Error(`Unknown trigger type: ${trigger.trigger_type}`);
      }

      // Update trigger with result
      await this.db.updateWorkflowTrigger(trigger.id, {
        status: result.success ? 'completed' : 'failed',
        completed_at: new Date(),
        result: result.data,
        error_message: result.error
      });

      logger.info('Workflow trigger executed successfully', {
        triggerId: trigger.id,
        success: result.success,
        executionTime: result.execution_time_ms
      });

      return result;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      logger.error('Workflow trigger execution failed', {
        triggerId: trigger.id,
        error: errorMessage,
        executionTime
      });

      return {
        success: false,
        error: errorMessage,
        execution_time_ms: executionTime
      };
    }
  }

  /**
   * Execute Codegen workflow trigger
   */
  private async executeCodegenTrigger(trigger: WorkflowTrigger): Promise<WorkflowTriggerResult> {
    const startTime = Date.now();
    const config = CodegenTriggerConfigSchema.parse(trigger.trigger_config);
    
    try {
      // Get task details
      const task = await this.db.getTask(trigger.task_id);
      if (!task) {
        throw new Error(`Task ${trigger.task_id} not found`);
      }

      // Prepare Codegen API request
      const payload = {
        task: {
          id: task.id,
          title: task.title,
          description: task.description,
          requirements: task.parsed_requirements,
          files: config.target_files
        },
        config: {
          repository_url: config.repository_url,
          branch_name: config.branch_name,
          auto_trigger: config.auto_trigger,
          review_required: config.review_required,
          timeout_minutes: config.timeout_minutes
        },
        instructions: config.agent_instructions || task.description
      };

      // Call Codegen API
      const response = await axios.post(
        `${this.codegenApiUrl}/api/v1/agents/create-task`,
        payload,
        {
          headers: {
            'Authorization': `Bearer ${this.codegenApiKey}`,
            'Content-Type': 'application/json'
          },
          timeout: config.timeout_minutes * 60 * 1000
        }
      );

      return {
        success: true,
        data: response.data,
        execution_time_ms: Date.now() - startTime,
        metadata: {
          agent_id: response.data.agent_id,
          task_url: response.data.task_url
        }
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Codegen trigger failed',
        execution_time_ms: Date.now() - startTime
      };
    }
  }

  /**
   * Execute Claude Code workflow trigger
   */
  private async executeClaudeCodeTrigger(trigger: WorkflowTrigger): Promise<WorkflowTriggerResult> {
    const startTime = Date.now();
    const config = ClaudeCodeTriggerConfigSchema.parse(trigger.trigger_config);
    
    try {
      // Get task details
      const task = await this.db.getTask(trigger.task_id);
      if (!task) {
        throw new Error(`Task ${trigger.task_id} not found`);
      }

      // Prepare Claude Code API request
      const payload = {
        task_id: task.id,
        validation_type: config.validation_type,
        auto_fix: config.auto_fix,
        checks: {
          test_coverage: config.test_coverage_required,
          security_scan: config.security_scan,
          performance_check: config.performance_check
        },
        code_context: {
          files: task.metadata?.files || [],
          description: task.description
        }
      };

      // Call Claude Code API
      const response = await axios.post(
        `${this.claudeCodeApiUrl}/api/v1/validate`,
        payload,
        {
          headers: {
            'Authorization': `Bearer ${this.claudeCodeApiKey}`,
            'Content-Type': 'application/json'
          },
          timeout: 300000 // 5 minutes
        }
      );

      return {
        success: true,
        data: response.data,
        execution_time_ms: Date.now() - startTime,
        metadata: {
          validation_id: response.data.validation_id,
          issues_found: response.data.issues?.length || 0
        }
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Claude Code trigger failed',
        execution_time_ms: Date.now() - startTime
      };
    }
  }

  /**
   * Execute webhook workflow trigger
   */
  private async executeWebhookTrigger(trigger: WorkflowTrigger): Promise<WorkflowTriggerResult> {
    const startTime = Date.now();
    const config = WebhookTriggerConfigSchema.parse(trigger.trigger_config);
    
    try {
      // Get task details for payload
      const task = await this.db.getTask(trigger.task_id);
      if (!task) {
        throw new Error(`Task ${trigger.task_id} not found`);
      }

      // Prepare headers
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...config.headers
      };

      // Add authentication
      if (config.authentication) {
        switch (config.authentication.type) {
          case 'bearer':
            headers['Authorization'] = `Bearer ${config.authentication.token}`;
            break;
          case 'basic':
            const credentials = Buffer.from(
              `${config.authentication.username}:${config.authentication.password}`
            ).toString('base64');
            headers['Authorization'] = `Basic ${credentials}`;
            break;
          case 'api_key':
            if (config.authentication.api_key_header && config.authentication.token) {
              headers[config.authentication.api_key_header] = config.authentication.token;
            }
            break;
        }
      }

      // Prepare payload
      let payload: any = {
        trigger_id: trigger.id,
        task: {
          id: task.id,
          title: task.title,
          description: task.description,
          status: task.status,
          priority: task.priority
        },
        timestamp: new Date().toISOString()
      };

      // Use custom payload template if provided
      if (config.payload_template) {
        try {
          payload = JSON.parse(
            config.payload_template
              .replace(/\{\{task\.id\}\}/g, task.id)
              .replace(/\{\{task\.title\}\}/g, task.title)
              .replace(/\{\{task\.description\}\}/g, task.description || '')
              .replace(/\{\{task\.status\}\}/g, task.status)
              .replace(/\{\{trigger\.id\}\}/g, trigger.id)
          );
        } catch (error) {
          logger.warn('Failed to parse payload template, using default', { error });
        }
      }

      // Make webhook request
      const response = await axios({
        method: config.method,
        url: config.endpoint,
        headers,
        data: config.method !== 'GET' ? payload : undefined,
        params: config.method === 'GET' ? payload : undefined,
        timeout: 30000
      });

      return {
        success: true,
        data: response.data,
        execution_time_ms: Date.now() - startTime,
        metadata: {
          status_code: response.status,
          response_headers: response.headers
        }
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Webhook trigger failed',
        execution_time_ms: Date.now() - startTime
      };
    }
  }

  /**
   * Execute manual workflow trigger
   */
  private async executeManualTrigger(trigger: WorkflowTrigger): Promise<WorkflowTriggerResult> {
    const startTime = Date.now();
    const config = ManualTriggerConfigSchema.parse(trigger.trigger_config);
    
    try {
      // For manual triggers, we just mark them as pending approval
      // The actual execution happens when approved through the UI/API
      
      if (config.approval_required) {
        // Update trigger to pending approval status
        await this.db.updateWorkflowTrigger(trigger.id, {
          status: 'pending_approval'
        });

        return {
          success: true,
          data: {
            status: 'pending_approval',
            approvers: config.approvers,
            instructions: config.instructions
          },
          execution_time_ms: Date.now() - startTime,
          metadata: {
            requires_approval: true
          }
        };
      } else {
        // Auto-approve if no approval required
        return {
          success: true,
          data: {
            status: 'approved',
            auto_approved: true
          },
          execution_time_ms: Date.now() - startTime
        };
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Manual trigger failed',
        execution_time_ms: Date.now() - startTime
      };
    }
  }

  /**
   * Execute scheduled workflow trigger
   */
  private async executeScheduledTrigger(trigger: WorkflowTrigger): Promise<WorkflowTriggerResult> {
    const startTime = Date.now();
    const config = ScheduledTriggerConfigSchema.parse(trigger.trigger_config);
    
    try {
      // Check if max executions reached
      if (config.max_executions && config.execution_count >= config.max_executions) {
        return {
          success: false,
          error: 'Maximum executions reached',
          execution_time_ms: Date.now() - startTime
        };
      }

      // For scheduled triggers, we set up the cron job
      // The actual execution logic depends on the specific scheduled task
      
      const jobId = `scheduled_${trigger.id}`;
      
      if (!this.scheduledJobs.has(jobId)) {
        const job = new CronJob(
          config.cron_expression,
          async () => {
            logger.info('Executing scheduled trigger', { triggerId: trigger.id });
            
            // Update execution count
            const updatedConfig = {
              ...config,
              execution_count: config.execution_count + 1
            };
            
            await this.db.updateWorkflowTrigger(trigger.id, {
              trigger_config: updatedConfig
            });
            
            // Here you would implement the actual scheduled task logic
            // For now, we just log the execution
            logger.info('Scheduled trigger executed', { 
              triggerId: trigger.id,
              executionCount: updatedConfig.execution_count
            });
          },
          null,
          true,
          config.timezone
        );
        
        this.scheduledJobs.set(jobId, job);
      }

      return {
        success: true,
        data: {
          status: 'scheduled',
          cron_expression: config.cron_expression,
          next_execution: this.scheduledJobs.get(jobId)?.nextDate()?.toISOString()
        },
        execution_time_ms: Date.now() - startTime,
        metadata: {
          job_id: jobId
        }
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Scheduled trigger failed',
        execution_time_ms: Date.now() - startTime
      };
    }
  }

  /**
   * Create a new workflow trigger
   */
  async createTrigger(
    taskId: string,
    triggerType: 'codegen' | 'claude_code' | 'webhook' | 'manual' | 'scheduled',
    config: any
  ): Promise<WorkflowTrigger> {
    logger.info('Creating workflow trigger', { taskId, triggerType });

    // Validate config based on trigger type
    let validatedConfig: any;
    switch (triggerType) {
      case 'codegen':
        validatedConfig = CodegenTriggerConfigSchema.parse(config);
        break;
      case 'claude_code':
        validatedConfig = ClaudeCodeTriggerConfigSchema.parse(config);
        break;
      case 'webhook':
        validatedConfig = WebhookTriggerConfigSchema.parse(config);
        break;
      case 'manual':
        validatedConfig = ManualTriggerConfigSchema.parse(config);
        break;
      case 'scheduled':
        validatedConfig = ScheduledTriggerConfigSchema.parse(config);
        break;
      default:
        throw new Error(`Invalid trigger type: ${triggerType}`);
    }

    const trigger = await this.db.createWorkflowTrigger({
      task_id: taskId,
      trigger_type: triggerType,
      trigger_config: validatedConfig,
      status: 'pending'
    });

    logger.info('Workflow trigger created', { triggerId: trigger.id });
    return trigger;
  }

  /**
   * Cancel a scheduled trigger
   */
  async cancelScheduledTrigger(triggerId: string): Promise<void> {
    const jobId = `scheduled_${triggerId}`;
    const job = this.scheduledJobs.get(jobId);
    
    if (job) {
      job.stop();
      this.scheduledJobs.delete(jobId);
      logger.info('Scheduled trigger cancelled', { triggerId });
    }

    await this.db.updateWorkflowTrigger(triggerId, {
      status: 'cancelled'
    });
  }

  /**
   * Get trigger execution history
   */
  async getTriggerHistory(taskId: string): Promise<WorkflowTrigger[]> {
    const query = 'SELECT * FROM workflow_triggers WHERE task_id = $1 ORDER BY created_at DESC';
    const result = await this.db.query(query, [taskId]);
    return result.rows;
  }

  /**
   * Retry a failed trigger
   */
  async retryTrigger(triggerId: string): Promise<WorkflowTriggerResult> {
    const trigger = await this.db.query(
      'SELECT * FROM workflow_triggers WHERE id = $1',
      [triggerId]
    );

    if (trigger.rows.length === 0) {
      throw new Error(`Trigger ${triggerId} not found`);
    }

    const triggerData = trigger.rows[0];
    
    if (triggerData.retry_count >= triggerData.max_retries) {
      throw new Error('Maximum retry attempts exceeded');
    }

    // Reset trigger status and execute
    await this.db.updateWorkflowTrigger(triggerId, {
      status: 'pending',
      error_message: null
    });

    return this.executeTrigger(triggerData);
  }

  /**
   * Cleanup completed and old triggers
   */
  async cleanupTriggers(olderThanDays = 30): Promise<void> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);

    const query = `
      DELETE FROM workflow_triggers 
      WHERE status IN ('completed', 'failed', 'cancelled') 
      AND created_at < $1
    `;
    
    const result = await this.db.query(query, [cutoffDate]);
    logger.info('Cleaned up old triggers', { deletedCount: result.rowCount });
  }

  /**
   * Shutdown and cleanup
   */
  async shutdown(): Promise<void> {
    logger.info('Shutting down workflow trigger manager');
    
    // Stop all scheduled jobs
    for (const [jobId, job] of this.scheduledJobs) {
      job.stop();
      logger.info('Stopped scheduled job', { jobId });
    }
    
    this.scheduledJobs.clear();
  }
}

