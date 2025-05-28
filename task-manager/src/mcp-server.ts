import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { DatabaseClient } from './database-client.js';
import { TaskParser } from './task-parser.js';
import { DependencyAnalyzer } from './dependency-analyzer.js';
import { WorkflowTriggerManager } from './workflow-trigger.js';
import { logger } from './utils/logger.js';

// Tool schemas
const CreateTaskSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
  natural_language_input: z.string().optional(),
  project_id: z.string().uuid().optional(),
  priority: z.enum(['low', 'medium', 'high', 'critical']).default('medium'),
  complexity: z.enum(['simple', 'moderate', 'complex', 'epic']).default('moderate'),
  estimated_hours: z.number().optional(),
  assignee: z.string().optional(),
  tags: z.array(z.string()).default([]),
  due_date: z.string().datetime().optional(),
  auto_parse: z.boolean().default(true)
});

const UpdateTaskSchema = z.object({
  task_id: z.string().uuid(),
  title: z.string().optional(),
  description: z.string().optional(),
  status: z.enum(['pending', 'in_progress', 'blocked', 'review', 'completed', 'cancelled', 'failed']).optional(),
  priority: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  complexity: z.enum(['simple', 'moderate', 'complex', 'epic']).optional(),
  estimated_hours: z.number().optional(),
  actual_hours: z.number().optional(),
  assignee: z.string().optional(),
  tags: z.array(z.string()).optional(),
  due_date: z.string().datetime().optional()
});

const AddDependencySchema = z.object({
  task_id: z.string().uuid(),
  depends_on_task_id: z.string().uuid(),
  dependency_type: z.string().default('blocks')
});

const CreateWorkflowTriggerSchema = z.object({
  task_id: z.string().uuid(),
  trigger_type: z.enum(['codegen', 'claude_code', 'webhook', 'manual', 'scheduled']),
  config: z.record(z.any())
});

const SearchTasksSchema = z.object({
  query: z.string().optional(),
  project_id: z.string().uuid().optional(),
  status: z.string().optional(),
  priority: z.string().optional(),
  assignee: z.string().optional(),
  limit: z.number().default(10),
  offset: z.number().default(0)
});

const AnalyzeDependenciesSchema = z.object({
  project_id: z.string().uuid().optional()
});

export class EnhancedTaskManagerMCPServer {
  private server: Server;
  private db: DatabaseClient;
  private taskParser: TaskParser;
  private dependencyAnalyzer: DependencyAnalyzer;
  private workflowManager: WorkflowTriggerManager;

  constructor(
    db: DatabaseClient,
    workflowConfig: {
      codegenApiUrl: string;
      codegenApiKey: string;
      claudeCodeApiUrl: string;
      claudeCodeApiKey: string;
    }
  ) {
    this.db = db;
    this.taskParser = new TaskParser();
    this.dependencyAnalyzer = new DependencyAnalyzer();
    this.workflowManager = new WorkflowTriggerManager(db, workflowConfig);

    this.server = new Server(
      {
        name: 'enhanced-task-manager',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
  }

  private setupToolHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'create_task',
            description: 'Create a new task with natural language parsing',
            inputSchema: {
              type: 'object',
              properties: {
                title: { type: 'string', description: 'Task title' },
                description: { type: 'string', description: 'Task description' },
                natural_language_input: { type: 'string', description: 'Natural language task description for parsing' },
                project_id: { type: 'string', description: 'Project UUID' },
                priority: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] },
                complexity: { type: 'string', enum: ['simple', 'moderate', 'complex', 'epic'] },
                estimated_hours: { type: 'number', description: 'Estimated hours to complete' },
                assignee: { type: 'string', description: 'Task assignee' },
                tags: { type: 'array', items: { type: 'string' } },
                due_date: { type: 'string', format: 'date-time' },
                auto_parse: { type: 'boolean', description: 'Enable automatic natural language parsing' }
              },
              required: ['title']
            }
          },
          {
            name: 'update_task',
            description: 'Update an existing task',
            inputSchema: {
              type: 'object',
              properties: {
                task_id: { type: 'string', description: 'Task UUID' },
                title: { type: 'string' },
                description: { type: 'string' },
                status: { type: 'string', enum: ['pending', 'in_progress', 'blocked', 'review', 'completed', 'cancelled', 'failed'] },
                priority: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] },
                complexity: { type: 'string', enum: ['simple', 'moderate', 'complex', 'epic'] },
                estimated_hours: { type: 'number' },
                actual_hours: { type: 'number' },
                assignee: { type: 'string' },
                tags: { type: 'array', items: { type: 'string' } },
                due_date: { type: 'string', format: 'date-time' }
              },
              required: ['task_id']
            }
          },
          {
            name: 'get_task',
            description: 'Get task details by ID',
            inputSchema: {
              type: 'object',
              properties: {
                task_id: { type: 'string', description: 'Task UUID' }
              },
              required: ['task_id']
            }
          },
          {
            name: 'search_tasks',
            description: 'Search and filter tasks',
            inputSchema: {
              type: 'object',
              properties: {
                query: { type: 'string', description: 'Search query' },
                project_id: { type: 'string', description: 'Project UUID' },
                status: { type: 'string' },
                priority: { type: 'string' },
                assignee: { type: 'string' },
                limit: { type: 'number', default: 10 },
                offset: { type: 'number', default: 0 }
              }
            }
          },
          {
            name: 'add_dependency',
            description: 'Add a dependency between tasks',
            inputSchema: {
              type: 'object',
              properties: {
                task_id: { type: 'string', description: 'Task UUID that depends on another' },
                depends_on_task_id: { type: 'string', description: 'Task UUID that is depended upon' },
                dependency_type: { type: 'string', default: 'blocks', description: 'Type of dependency' }
              },
              required: ['task_id', 'depends_on_task_id']
            }
          },
          {
            name: 'remove_dependency',
            description: 'Remove a dependency between tasks',
            inputSchema: {
              type: 'object',
              properties: {
                task_id: { type: 'string', description: 'Task UUID' },
                depends_on_task_id: { type: 'string', description: 'Dependency task UUID' }
              },
              required: ['task_id', 'depends_on_task_id']
            }
          },
          {
            name: 'analyze_dependencies',
            description: 'Analyze task dependencies and generate insights',
            inputSchema: {
              type: 'object',
              properties: {
                project_id: { type: 'string', description: 'Project UUID (optional)' }
              }
            }
          },
          {
            name: 'get_ready_tasks',
            description: 'Get tasks that are ready to start (no incomplete dependencies)',
            inputSchema: {
              type: 'object',
              properties: {
                project_id: { type: 'string', description: 'Project UUID (optional)' },
                assignee: { type: 'string', description: 'Filter by assignee (optional)' }
              }
            }
          },
          {
            name: 'suggest_task_ordering',
            description: 'Get suggested optimal task execution order',
            inputSchema: {
              type: 'object',
              properties: {
                project_id: { type: 'string', description: 'Project UUID (optional)' }
              }
            }
          },
          {
            name: 'create_workflow_trigger',
            description: 'Create a workflow trigger for a task',
            inputSchema: {
              type: 'object',
              properties: {
                task_id: { type: 'string', description: 'Task UUID' },
                trigger_type: { type: 'string', enum: ['codegen', 'claude_code', 'webhook', 'manual', 'scheduled'] },
                config: { type: 'object', description: 'Trigger configuration' }
              },
              required: ['task_id', 'trigger_type', 'config']
            }
          },
          {
            name: 'execute_workflow_trigger',
            description: 'Execute a workflow trigger',
            inputSchema: {
              type: 'object',
              properties: {
                trigger_id: { type: 'string', description: 'Trigger UUID' }
              },
              required: ['trigger_id']
            }
          },
          {
            name: 'parse_natural_language',
            description: 'Parse natural language input into structured task requirements',
            inputSchema: {
              type: 'object',
              properties: {
                input: { type: 'string', description: 'Natural language task description' },
                context: { 
                  type: 'object', 
                  description: 'Additional context for parsing',
                  properties: {
                    project_context: { type: 'string' },
                    existing_tasks: { type: 'array' },
                    user_preferences: { type: 'object' }
                  }
                }
              },
              required: ['input']
            }
          },
          {
            name: 'get_task_statistics',
            description: 'Get task statistics and analytics',
            inputSchema: {
              type: 'object',
              properties: {
                project_id: { type: 'string', description: 'Project UUID (optional)' }
              }
            }
          },
          {
            name: 'create_project',
            description: 'Create a new project',
            inputSchema: {
              type: 'object',
              properties: {
                name: { type: 'string', description: 'Project name' },
                description: { type: 'string', description: 'Project description' },
                repository_url: { type: 'string', description: 'Repository URL' },
                branch_name: { type: 'string', default: 'main' }
              },
              required: ['name']
            }
          },
          {
            name: 'list_projects',
            description: 'List all projects',
            inputSchema: {
              type: 'object',
              properties: {}
            }
          }
        ]
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'create_task':
            return await this.handleCreateTask(args);
          case 'update_task':
            return await this.handleUpdateTask(args);
          case 'get_task':
            return await this.handleGetTask(args);
          case 'search_tasks':
            return await this.handleSearchTasks(args);
          case 'add_dependency':
            return await this.handleAddDependency(args);
          case 'remove_dependency':
            return await this.handleRemoveDependency(args);
          case 'analyze_dependencies':
            return await this.handleAnalyzeDependencies(args);
          case 'get_ready_tasks':
            return await this.handleGetReadyTasks(args);
          case 'suggest_task_ordering':
            return await this.handleSuggestTaskOrdering(args);
          case 'create_workflow_trigger':
            return await this.handleCreateWorkflowTrigger(args);
          case 'execute_workflow_trigger':
            return await this.handleExecuteWorkflowTrigger(args);
          case 'parse_natural_language':
            return await this.handleParseNaturalLanguage(args);
          case 'get_task_statistics':
            return await this.handleGetTaskStatistics(args);
          case 'create_project':
            return await this.handleCreateProject(args);
          case 'list_projects':
            return await this.handleListProjects(args);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
      } catch (error) {
        logger.error('Tool execution failed', { tool: name, error });
        
        if (error instanceof McpError) {
          throw error;
        }
        
        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    });
  }

  private async handleCreateTask(args: any) {
    const params = CreateTaskSchema.parse(args);
    
    let taskData: any = {
      title: params.title,
      description: params.description,
      project_id: params.project_id,
      priority: params.priority,
      complexity: params.complexity,
      estimated_hours: params.estimated_hours,
      assignee: params.assignee,
      tags: params.tags,
      due_date: params.due_date ? new Date(params.due_date) : undefined
    };

    // Parse natural language input if provided and auto_parse is enabled
    if (params.auto_parse && (params.natural_language_input || params.description)) {
      const inputText = params.natural_language_input || params.description || '';
      
      try {
        const parsed = await this.taskParser.parseTaskRequirement(inputText);
        
        // Merge parsed data with provided params (params take precedence)
        taskData = {
          ...taskData,
          title: params.title || parsed.title,
          description: params.description || parsed.description,
          priority: params.priority !== 'medium' ? params.priority : parsed.priority,
          complexity: params.complexity !== 'moderate' ? params.complexity : parsed.complexity,
          estimated_hours: params.estimated_hours || parsed.estimated_hours,
          tags: params.tags.length > 0 ? params.tags : parsed.tags,
          natural_language_input: inputText,
          parsed_requirements: parsed
        };
      } catch (error) {
        logger.warn('Natural language parsing failed, using provided data', { error });
        taskData.natural_language_input = inputText;
      }
    }

    const task = await this.db.createTask(taskData);

    // Create workflow triggers if specified in parsed requirements
    if (taskData.parsed_requirements?.workflow_triggers) {
      for (const triggerConfig of taskData.parsed_requirements.workflow_triggers) {
        try {
          await this.workflowManager.createTrigger(
            task.id,
            triggerConfig.type,
            triggerConfig.config
          );
        } catch (error) {
          logger.warn('Failed to create workflow trigger', { error, triggerConfig });
        }
      }
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            success: true,
            task: task,
            parsed_requirements: taskData.parsed_requirements
          }, null, 2)
        }
      ]
    };
  }

  private async handleUpdateTask(args: any) {
    const params = UpdateTaskSchema.parse(args);
    
    const updates: any = {};
    Object.keys(params).forEach(key => {
      if (key !== 'task_id' && params[key] !== undefined) {
        if (key === 'due_date' && params[key]) {
          updates[key] = new Date(params[key]);
        } else {
          updates[key] = params[key];
        }
      }
    });

    const task = await this.db.updateTask(params.task_id, updates);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, task }, null, 2)
        }
      ]
    };
  }

  private async handleGetTask(args: any) {
    const { task_id } = args;
    const task = await this.db.getTask(task_id);
    
    if (!task) {
      throw new McpError(ErrorCode.InvalidRequest, `Task ${task_id} not found`);
    }

    // Get dependencies
    const dependencies = await this.db.getTaskDependencies(task_id);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ 
            success: true, 
            task, 
            dependencies 
          }, null, 2)
        }
      ]
    };
  }

  private async handleSearchTasks(args: any) {
    const params = SearchTasksSchema.parse(args);
    
    let tasks;
    if (params.query) {
      tasks = await this.db.searchTasks(params.query, params.limit);
    } else {
      tasks = await this.db.listTasks({
        project_id: params.project_id,
        status: params.status,
        priority: params.priority,
        assignee: params.assignee,
        limit: params.limit,
        offset: params.offset
      });
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ 
            success: true, 
            tasks,
            count: tasks.length 
          }, null, 2)
        }
      ]
    };
  }

  private async handleAddDependency(args: any) {
    const params = AddDependencySchema.parse(args);
    
    const dependency = await this.db.addTaskDependency(
      params.task_id,
      params.depends_on_task_id,
      params.dependency_type
    );

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, dependency }, null, 2)
        }
      ]
    };
  }

  private async handleRemoveDependency(args: any) {
    const { task_id, depends_on_task_id } = args;
    
    await this.db.removeTaskDependency(task_id, depends_on_task_id);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, message: 'Dependency removed' }, null, 2)
        }
      ]
    };
  }

  private async handleAnalyzeDependencies(args: any) {
    const params = AnalyzeDependenciesSchema.parse(args);
    
    const { nodes, edges } = await this.db.getDependencyGraph(params.project_id);
    
    this.dependencyAnalyzer.buildGraph(nodes, edges);
    const analysis = this.dependencyAnalyzer.analyze();

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ 
            success: true, 
            analysis,
            graph_stats: {
              nodes: nodes.length,
              edges: edges.length
            }
          }, null, 2)
        }
      ]
    };
  }

  private async handleGetReadyTasks(args: any) {
    const { project_id, assignee } = args;
    
    const { nodes, edges } = await this.db.getDependencyGraph(project_id);
    this.dependencyAnalyzer.buildGraph(nodes, edges);
    
    let readyTaskIds = this.dependencyAnalyzer.getReadyTasks();
    
    // Filter by assignee if specified
    if (assignee) {
      const readyTasks = await Promise.all(
        readyTaskIds.map(id => this.db.getTask(id))
      );
      readyTaskIds = readyTasks
        .filter(task => task?.assignee === assignee)
        .map(task => task!.id);
    }

    const readyTasks = await Promise.all(
      readyTaskIds.map(id => this.db.getTask(id))
    );

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ 
            success: true, 
            ready_tasks: readyTasks.filter(Boolean),
            count: readyTasks.length
          }, null, 2)
        }
      ]
    };
  }

  private async handleSuggestTaskOrdering(args: any) {
    const { project_id } = args;
    
    const { nodes, edges } = await this.db.getDependencyGraph(project_id);
    this.dependencyAnalyzer.buildGraph(nodes, edges);
    
    const ordering = this.dependencyAnalyzer.suggestTaskOrdering();
    const orderedTasks = await Promise.all(
      ordering.map(id => this.db.getTask(id))
    );

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ 
            success: true, 
            suggested_order: orderedTasks.filter(Boolean),
            task_ids: ordering
          }, null, 2)
        }
      ]
    };
  }

  private async handleCreateWorkflowTrigger(args: any) {
    const params = CreateWorkflowTriggerSchema.parse(args);
    
    const trigger = await this.workflowManager.createTrigger(
      params.task_id,
      params.trigger_type,
      params.config
    );

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, trigger }, null, 2)
        }
      ]
    };
  }

  private async handleExecuteWorkflowTrigger(args: any) {
    const { trigger_id } = args;
    
    const trigger = await this.db.query(
      'SELECT * FROM workflow_triggers WHERE id = $1',
      [trigger_id]
    );

    if (trigger.rows.length === 0) {
      throw new McpError(ErrorCode.InvalidRequest, `Trigger ${trigger_id} not found`);
    }

    const result = await this.workflowManager.executeTrigger(trigger.rows[0]);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, result }, null, 2)
        }
      ]
    };
  }

  private async handleParseNaturalLanguage(args: any) {
    const { input, context } = args;
    
    const parsed = await this.taskParser.parseTaskRequirement(input, context);
    const complexity = this.taskParser.analyzeTaskComplexity(parsed);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ 
            success: true, 
            parsed_requirements: parsed,
            complexity_analysis: complexity
          }, null, 2)
        }
      ]
    };
  }

  private async handleGetTaskStatistics(args: any) {
    const { project_id } = args;
    
    const stats = await this.db.getTaskStatistics(project_id);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, statistics: stats }, null, 2)
        }
      ]
    };
  }

  private async handleCreateProject(args: any) {
    const { name, description, repository_url, branch_name } = args;
    
    const project = await this.db.createProject({
      name,
      description,
      repository_url,
      branch_name: branch_name || 'main',
      metadata: {}
    });

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, project }, null, 2)
        }
      ]
    };
  }

  private async handleListProjects(args: any) {
    const projects = await this.db.listProjects();

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ 
            success: true, 
            projects,
            count: projects.length 
          }, null, 2)
        }
      ]
    };
  }

  async start(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    logger.info('Enhanced Task Manager MCP Server started');
  }

  async stop(): Promise<void> {
    await this.workflowManager.shutdown();
    await this.db.disconnect();
    logger.info('Enhanced Task Manager MCP Server stopped');
  }
}

