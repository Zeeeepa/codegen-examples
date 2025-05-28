import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { DatabaseClient } from '../src/database-client.js';
import { EnhancedTaskManagerMCPServer } from '../src/mcp-server.js';

describe('Enhanced Task Manager MCP Server', () => {
  let db: DatabaseClient;
  let server: EnhancedTaskManagerMCPServer;

  beforeEach(async () => {
    // Setup test database
    db = new DatabaseClient({
      host: process.env.TEST_DB_HOST || 'localhost',
      port: parseInt(process.env.TEST_DB_PORT || '5432'),
      database: process.env.TEST_DB_NAME || 'task_manager_test',
      user: process.env.TEST_DB_USER || 'test_user',
      password: process.env.TEST_DB_PASSWORD || 'test_password'
    });

    await db.connect();

    // Initialize server
    server = new EnhancedTaskManagerMCPServer(db, {
      codegenApiUrl: 'http://localhost:3000',
      codegenApiKey: 'test-key',
      claudeCodeApiUrl: 'http://localhost:3001',
      claudeCodeApiKey: 'test-key'
    });
  });

  afterEach(async () => {
    await db.disconnect();
  });

  describe('Task Management', () => {
    it('should create a task with natural language parsing', async () => {
      const taskData = {
        title: 'Test Task',
        natural_language_input: 'Create a simple login form with email and password fields. This is a high priority task.',
        auto_parse: true
      };

      // Mock the tool call
      const result = await server['handleCreateTask'](taskData);
      
      expect(result.content[0].text).toContain('success');
      const response = JSON.parse(result.content[0].text);
      expect(response.success).toBe(true);
      expect(response.task.title).toBe('Test Task');
      expect(response.parsed_requirements).toBeDefined();
    });

    it('should update task status', async () => {
      // First create a task
      const createResult = await server['handleCreateTask']({
        title: 'Test Task for Update'
      });
      
      const createResponse = JSON.parse(createResult.content[0].text);
      const taskId = createResponse.task.id;

      // Update the task
      const updateResult = await server['handleUpdateTask']({
        task_id: taskId,
        status: 'in_progress',
        actual_hours: 5
      });

      const updateResponse = JSON.parse(updateResult.content[0].text);
      expect(updateResponse.success).toBe(true);
      expect(updateResponse.task.status).toBe('in_progress');
      expect(updateResponse.task.actual_hours).toBe(5);
    });

    it('should search tasks by query', async () => {
      // Create test tasks
      await server['handleCreateTask']({
        title: 'Authentication Task',
        description: 'Implement user authentication'
      });

      await server['handleCreateTask']({
        title: 'Database Task',
        description: 'Setup database schema'
      });

      // Search for authentication tasks
      const searchResult = await server['handleSearchTasks']({
        query: 'authentication',
        limit: 10
      });

      const searchResponse = JSON.parse(searchResult.content[0].text);
      expect(searchResponse.success).toBe(true);
      expect(searchResponse.tasks.length).toBeGreaterThan(0);
      expect(searchResponse.tasks[0].title).toContain('Authentication');
    });
  });

  describe('Dependency Management', () => {
    it('should add and analyze dependencies', async () => {
      // Create two tasks
      const task1Result = await server['handleCreateTask']({
        title: 'Setup Database'
      });
      const task1Response = JSON.parse(task1Result.content[0].text);
      const task1Id = task1Response.task.id;

      const task2Result = await server['handleCreateTask']({
        title: 'Create User Model'
      });
      const task2Response = JSON.parse(task2Result.content[0].text);
      const task2Id = task2Response.task.id;

      // Add dependency (task2 depends on task1)
      const depResult = await server['handleAddDependency']({
        task_id: task2Id,
        depends_on_task_id: task1Id,
        dependency_type: 'blocks'
      });

      const depResponse = JSON.parse(depResult.content[0].text);
      expect(depResponse.success).toBe(true);

      // Analyze dependencies
      const analysisResult = await server['handleAnalyzeDependencies']({});
      const analysisResponse = JSON.parse(analysisResult.content[0].text);
      
      expect(analysisResponse.success).toBe(true);
      expect(analysisResponse.analysis).toBeDefined();
      expect(analysisResponse.analysis.criticalPath).toContain(task1Id);
    });

    it('should get ready tasks', async () => {
      // Create a task with no dependencies
      await server['handleCreateTask']({
        title: 'Independent Task',
        status: 'pending'
      });

      const readyResult = await server['handleGetReadyTasks']({});
      const readyResponse = JSON.parse(readyResult.content[0].text);
      
      expect(readyResponse.success).toBe(true);
      expect(readyResponse.ready_tasks.length).toBeGreaterThan(0);
    });
  });

  describe('Natural Language Processing', () => {
    it('should parse natural language requirements', async () => {
      const input = 'Build a user registration system with email verification, password strength validation, and CAPTCHA protection. This is a critical security feature that needs to be completed in 3 weeks.';

      const parseResult = await server['handleParseNaturalLanguage']({
        input,
        context: {
          project_context: 'Web application security'
        }
      });

      const parseResponse = JSON.parse(parseResult.content[0].text);
      expect(parseResponse.success).toBe(true);
      expect(parseResponse.parsed_requirements.title).toContain('registration');
      expect(parseResponse.parsed_requirements.priority).toBe('critical');
      expect(parseResponse.parsed_requirements.tags).toContain('security');
      expect(parseResponse.complexity_analysis).toBeDefined();
    });

    it('should extract technical requirements', async () => {
      const input = 'Implement a REST API with JWT authentication, rate limiting, and Swagger documentation. Use Express.js and MongoDB.';

      const parseResult = await server['handleParseNaturalLanguage']({ input });
      const parseResponse = JSON.parse(parseResult.content[0].text);
      
      expect(parseResponse.parsed_requirements.technical_requirements.length).toBeGreaterThan(0);
      expect(parseResponse.parsed_requirements.tags).toContain('backend');
    });
  });

  describe('Workflow Triggers', () => {
    it('should create codegen workflow trigger', async () => {
      // Create a task first
      const taskResult = await server['handleCreateTask']({
        title: 'Test Task for Workflow'
      });
      const taskResponse = JSON.parse(taskResult.content[0].text);
      const taskId = taskResponse.task.id;

      // Create workflow trigger
      const triggerResult = await server['handleCreateWorkflowTrigger']({
        task_id: taskId,
        trigger_type: 'codegen',
        config: {
          auto_trigger: false,
          review_required: true,
          repository_url: 'https://github.com/test/repo',
          branch_name: 'feature/test'
        }
      });

      const triggerResponse = JSON.parse(triggerResult.content[0].text);
      expect(triggerResponse.success).toBe(true);
      expect(triggerResponse.trigger.trigger_type).toBe('codegen');
    });

    it('should create webhook trigger', async () => {
      const taskResult = await server['handleCreateTask']({
        title: 'Test Task for Webhook'
      });
      const taskResponse = JSON.parse(taskResult.content[0].text);
      const taskId = taskResponse.task.id;

      const triggerResult = await server['handleCreateWorkflowTrigger']({
        task_id: taskId,
        trigger_type: 'webhook',
        config: {
          endpoint: 'https://api.example.com/webhook',
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      });

      const triggerResponse = JSON.parse(triggerResult.content[0].text);
      expect(triggerResponse.success).toBe(true);
      expect(triggerResponse.trigger.trigger_type).toBe('webhook');
    });
  });

  describe('Project Management', () => {
    it('should create and list projects', async () => {
      // Create project
      const createResult = await server['handleCreateProject']({
        name: 'Test Project',
        description: 'A test project for unit testing',
        repository_url: 'https://github.com/test/project'
      });

      const createResponse = JSON.parse(createResult.content[0].text);
      expect(createResponse.success).toBe(true);
      expect(createResponse.project.name).toBe('Test Project');

      // List projects
      const listResult = await server['handleListProjects']({});
      const listResponse = JSON.parse(listResult.content[0].text);
      
      expect(listResponse.success).toBe(true);
      expect(listResponse.projects.length).toBeGreaterThan(0);
      expect(listResponse.projects.some(p => p.name === 'Test Project')).toBe(true);
    });
  });

  describe('Analytics', () => {
    it('should get task statistics', async () => {
      // Create some test tasks with different statuses
      await server['handleCreateTask']({
        title: 'Completed Task',
        status: 'completed'
      });

      await server['handleCreateTask']({
        title: 'Pending Task',
        status: 'pending'
      });

      const statsResult = await server['handleGetTaskStatistics']({});
      const statsResponse = JSON.parse(statsResult.content[0].text);
      
      expect(statsResponse.success).toBe(true);
      expect(statsResponse.statistics.total).toBeGreaterThan(0);
      expect(statsResponse.statistics.by_status).toBeDefined();
      expect(statsResponse.statistics.by_priority).toBeDefined();
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid task ID', async () => {
      try {
        await server['handleGetTask']({ task_id: 'invalid-uuid' });
        expect.fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('not found');
      }
    });

    it('should handle missing required parameters', async () => {
      try {
        await server['handleCreateTask']({});
        expect.fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('title');
      }
    });
  });
});

