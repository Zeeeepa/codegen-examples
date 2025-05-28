import natural from 'natural';
import nlp from 'compromise';
import { z } from 'zod';
import { logger } from './utils/logger.js';

// Schemas for parsed task data
export const ParsedRequirementSchema = z.object({
  title: z.string(),
  description: z.string(),
  priority: z.enum(['low', 'medium', 'high', 'critical']).default('medium'),
  complexity: z.enum(['simple', 'moderate', 'complex', 'epic']).default('moderate'),
  estimated_hours: z.number().optional(),
  tags: z.array(z.string()).default([]),
  dependencies: z.array(z.string()).default([]),
  acceptance_criteria: z.array(z.string()).default([]),
  technical_requirements: z.array(z.string()).default([]),
  files_to_modify: z.array(z.string()).default([]),
  workflow_triggers: z.array(z.object({
    type: z.enum(['codegen', 'claude_code', 'webhook', 'manual', 'scheduled']),
    config: z.record(z.any())
  })).default([])
});

export type ParsedRequirement = z.infer<typeof ParsedRequirementSchema>;

export interface TaskParsingContext {
  projectContext?: string;
  existingTasks?: Array<{ id: string; title: string; description?: string }>;
  codebaseContext?: string;
  userPreferences?: {
    defaultPriority?: string;
    defaultComplexity?: string;
    preferredWorkflows?: string[];
  };
}

export class TaskParser {
  private tokenizer: natural.WordTokenizer;
  private stemmer: typeof natural.PorterStemmer;
  private sentiment: typeof natural.SentimentAnalyzer;
  
  // Keywords for different categories
  private priorityKeywords = {
    critical: ['urgent', 'critical', 'emergency', 'asap', 'immediately', 'blocker', 'production'],
    high: ['important', 'high', 'priority', 'soon', 'needed', 'required'],
    medium: ['normal', 'medium', 'standard', 'regular'],
    low: ['low', 'minor', 'nice to have', 'optional', 'when possible']
  };

  private complexityKeywords = {
    simple: ['simple', 'easy', 'quick', 'small', 'minor', 'trivial', 'fix'],
    moderate: ['moderate', 'medium', 'standard', 'normal', 'update', 'modify'],
    complex: ['complex', 'difficult', 'large', 'major', 'refactor', 'redesign'],
    epic: ['epic', 'massive', 'complete', 'full', 'entire', 'architecture']
  };

  private workflowKeywords = {
    codegen: ['generate', 'create', 'build', 'implement', 'code', 'develop'],
    claude_code: ['validate', 'test', 'check', 'verify', 'debug', 'review'],
    webhook: ['integrate', 'connect', 'api', 'webhook', 'external'],
    manual: ['manual', 'human', 'review', 'approve', 'decision'],
    scheduled: ['schedule', 'periodic', 'recurring', 'automated', 'cron']
  };

  private technicalKeywords = {
    frontend: ['ui', 'frontend', 'react', 'vue', 'angular', 'component', 'interface'],
    backend: ['api', 'backend', 'server', 'database', 'service', 'endpoint'],
    database: ['database', 'db', 'sql', 'query', 'schema', 'migration'],
    testing: ['test', 'testing', 'unit', 'integration', 'e2e', 'spec'],
    documentation: ['docs', 'documentation', 'readme', 'guide', 'manual'],
    deployment: ['deploy', 'deployment', 'ci/cd', 'pipeline', 'release'],
    security: ['security', 'auth', 'authentication', 'authorization', 'encryption']
  };

  constructor() {
    this.tokenizer = new natural.WordTokenizer();
    this.stemmer = natural.PorterStemmer;
    this.sentiment = natural.SentimentAnalyzer;
  }

  /**
   * Parse natural language input into structured task requirements
   */
  async parseTaskRequirement(
    input: string, 
    context?: TaskParsingContext
  ): Promise<ParsedRequirement> {
    logger.info('Parsing task requirement', { input: input.substring(0, 100) });

    try {
      // Clean and normalize input
      const cleanInput = this.cleanInput(input);
      
      // Extract basic components
      const title = this.extractTitle(cleanInput);
      const description = this.extractDescription(cleanInput, title);
      
      // Analyze priority and complexity
      const priority = this.analyzePriority(cleanInput, context?.userPreferences?.defaultPriority);
      const complexity = this.analyzeComplexity(cleanInput, context?.userPreferences?.defaultComplexity);
      
      // Extract time estimates
      const estimatedHours = this.extractTimeEstimate(cleanInput);
      
      // Extract tags and categories
      const tags = this.extractTags(cleanInput);
      
      // Extract dependencies
      const dependencies = this.extractDependencies(cleanInput, context?.existingTasks);
      
      // Extract acceptance criteria
      const acceptanceCriteria = this.extractAcceptanceCriteria(cleanInput);
      
      // Extract technical requirements
      const technicalRequirements = this.extractTechnicalRequirements(cleanInput);
      
      // Extract files to modify
      const filesToModify = this.extractFilesToModify(cleanInput);
      
      // Determine workflow triggers
      const workflowTriggers = this.determineWorkflowTriggers(cleanInput, context);

      const parsed: ParsedRequirement = {
        title,
        description,
        priority,
        complexity,
        estimated_hours: estimatedHours,
        tags,
        dependencies,
        acceptance_criteria: acceptanceCriteria,
        technical_requirements: technicalRequirements,
        files_to_modify: filesToModify,
        workflow_triggers: workflowTriggers
      };

      logger.info('Successfully parsed task requirement', { 
        title, 
        priority, 
        complexity, 
        tagsCount: tags.length 
      });

      return ParsedRequirementSchema.parse(parsed);
    } catch (error) {
      logger.error('Failed to parse task requirement', { error, input });
      throw new Error(`Task parsing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Extract multiple tasks from a complex input
   */
  async parseMultipleTasks(
    input: string,
    context?: TaskParsingContext
  ): Promise<ParsedRequirement[]> {
    logger.info('Parsing multiple tasks from input');

    // Split input into potential task segments
    const segments = this.splitIntoTaskSegments(input);
    
    const tasks: ParsedRequirement[] = [];
    
    for (const segment of segments) {
      if (this.isValidTaskSegment(segment)) {
        try {
          const task = await this.parseTaskRequirement(segment, context);
          tasks.push(task);
        } catch (error) {
          logger.warn('Failed to parse task segment', { segment, error });
        }
      }
    }

    logger.info(`Parsed ${tasks.length} tasks from input`);
    return tasks;
  }

  private cleanInput(input: string): string {
    return input
      .trim()
      .replace(/\s+/g, ' ')
      .replace(/[^\w\s\-.,!?()[\]{}:;]/g, '');
  }

  private extractTitle(input: string): string {
    // Try to find a clear title pattern
    const titlePatterns = [
      /^(.+?)(?:\n|\.|\?|!)/,  // First sentence
      /(?:task|todo|implement|create|build|fix|update):\s*(.+?)(?:\n|$)/i,
      /^(.{1,80}?)(?:\s+(?:that|which|where|when|because))/i
    ];

    for (const pattern of titlePatterns) {
      const match = input.match(pattern);
      if (match && match[1]) {
        return match[1].trim();
      }
    }

    // Fallback: use first 80 characters
    return input.substring(0, 80).trim();
  }

  private extractDescription(input: string, title: string): string {
    // Remove the title from input to get description
    let description = input.replace(title, '').trim();
    
    // If description is too short, use the full input
    if (description.length < 20) {
      description = input;
    }

    return description;
  }

  private analyzePriority(input: string, defaultPriority?: string): 'low' | 'medium' | 'high' | 'critical' {
    const lowerInput = input.toLowerCase();
    
    for (const [priority, keywords] of Object.entries(this.priorityKeywords)) {
      if (keywords.some(keyword => lowerInput.includes(keyword))) {
        return priority as 'low' | 'medium' | 'high' | 'critical';
      }
    }

    return (defaultPriority as 'low' | 'medium' | 'high' | 'critical') || 'medium';
  }

  private analyzeComplexity(input: string, defaultComplexity?: string): 'simple' | 'moderate' | 'complex' | 'epic' {
    const lowerInput = input.toLowerCase();
    
    for (const [complexity, keywords] of Object.entries(this.complexityKeywords)) {
      if (keywords.some(keyword => lowerInput.includes(keyword))) {
        return complexity as 'simple' | 'moderate' | 'complex' | 'epic';
      }
    }

    // Analyze length and complexity indicators
    const wordCount = input.split(/\s+/).length;
    if (wordCount > 200) return 'epic';
    if (wordCount > 100) return 'complex';
    if (wordCount < 20) return 'simple';

    return (defaultComplexity as 'simple' | 'moderate' | 'complex' | 'epic') || 'moderate';
  }

  private extractTimeEstimate(input: string): number | undefined {
    const timePatterns = [
      /(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)/i,
      /(\d+(?:\.\d+)?)\s*(?:days?)\s*(?:\*\s*8)?/i,  // Convert days to hours
      /(\d+(?:\.\d+)?)\s*(?:weeks?)\s*(?:\*\s*40)?/i  // Convert weeks to hours
    ];

    for (const pattern of timePatterns) {
      const match = input.match(pattern);
      if (match) {
        let hours = parseFloat(match[1]);
        
        // Convert days/weeks to hours
        if (pattern.source.includes('days')) {
          hours *= 8;
        } else if (pattern.source.includes('weeks')) {
          hours *= 40;
        }
        
        return hours;
      }
    }

    return undefined;
  }

  private extractTags(input: string): string[] {
    const tags = new Set<string>();
    
    // Extract hashtags
    const hashtagMatches = input.match(/#(\w+)/g);
    if (hashtagMatches) {
      hashtagMatches.forEach(tag => tags.add(tag.substring(1).toLowerCase()));
    }

    // Extract technical categories
    for (const [category, keywords] of Object.entries(this.technicalKeywords)) {
      if (keywords.some(keyword => input.toLowerCase().includes(keyword))) {
        tags.add(category);
      }
    }

    // Extract programming languages
    const languages = ['javascript', 'typescript', 'python', 'java', 'go', 'rust', 'php', 'ruby'];
    languages.forEach(lang => {
      if (input.toLowerCase().includes(lang)) {
        tags.add(lang);
      }
    });

    return Array.from(tags);
  }

  private extractDependencies(input: string, existingTasks?: Array<{ id: string; title: string }>): string[] {
    const dependencies: string[] = [];
    
    // Look for explicit dependency patterns
    const dependencyPatterns = [
      /(?:depends on|requires|needs|after|blocked by)\s+(.+?)(?:\n|$|\.)/gi,
      /(?:prerequisite|dependency):\s*(.+?)(?:\n|$|\.)/gi
    ];

    for (const pattern of dependencyPatterns) {
      const matches = input.matchAll(pattern);
      for (const match of matches) {
        if (match[1]) {
          dependencies.push(match[1].trim());
        }
      }
    }

    // Try to match against existing tasks
    if (existingTasks) {
      existingTasks.forEach(task => {
        if (input.toLowerCase().includes(task.title.toLowerCase())) {
          dependencies.push(task.id);
        }
      });
    }

    return dependencies;
  }

  private extractAcceptanceCriteria(input: string): string[] {
    const criteria: string[] = [];
    
    // Look for acceptance criteria patterns
    const patterns = [
      /(?:acceptance criteria|ac|criteria):\s*(.+?)(?:\n\n|$)/gis,
      /(?:should|must|will):\s*(.+?)(?:\n|$)/gi,
      /✓\s*(.+?)(?:\n|$)/g,
      /-\s*(.+?)(?:\n|$)/g
    ];

    for (const pattern of patterns) {
      const matches = input.matchAll(pattern);
      for (const match of matches) {
        if (match[1]) {
          const criterion = match[1].trim();
          if (criterion.length > 10) {  // Filter out very short criteria
            criteria.push(criterion);
          }
        }
      }
    }

    return criteria;
  }

  private extractTechnicalRequirements(input: string): string[] {
    const requirements: string[] = [];
    
    // Look for technical requirement patterns
    const patterns = [
      /(?:technical requirements|tech req|requirements):\s*(.+?)(?:\n\n|$)/gis,
      /(?:use|implement|integrate)\s+(.+?)(?:\n|$|\.)/gi,
      /(?:framework|library|tool):\s*(.+?)(?:\n|$)/gi
    ];

    for (const pattern of patterns) {
      const matches = input.matchAll(pattern);
      for (const match of matches) {
        if (match[1]) {
          requirements.push(match[1].trim());
        }
      }
    }

    return requirements;
  }

  private extractFilesToModify(input: string): string[] {
    const files: string[] = [];
    
    // Look for file path patterns
    const filePatterns = [
      /(?:file|modify|update|edit):\s*([^\s]+\.[a-zA-Z]+)/gi,
      /([a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+\.[a-zA-Z]+)/g,
      /([a-zA-Z0-9_-]+\.[a-zA-Z]+)/g
    ];

    for (const pattern of filePatterns) {
      const matches = input.matchAll(pattern);
      for (const match of matches) {
        if (match[1]) {
          files.push(match[1]);
        }
      }
    }

    return [...new Set(files)];  // Remove duplicates
  }

  private determineWorkflowTriggers(
    input: string, 
    context?: TaskParsingContext
  ): Array<{ type: 'codegen' | 'claude_code' | 'webhook' | 'manual' | 'scheduled'; config: Record<string, any> }> {
    const triggers: Array<{ type: 'codegen' | 'claude_code' | 'webhook' | 'manual' | 'scheduled'; config: Record<string, any> }> = [];
    const lowerInput = input.toLowerCase();

    // Determine appropriate workflow triggers based on keywords
    for (const [triggerType, keywords] of Object.entries(this.workflowKeywords)) {
      if (keywords.some(keyword => lowerInput.includes(keyword))) {
        const config: Record<string, any> = {};
        
        switch (triggerType) {
          case 'codegen':
            config.auto_trigger = true;
            config.review_required = lowerInput.includes('review');
            break;
          case 'claude_code':
            config.validation_type = 'full';
            config.auto_fix = true;
            break;
          case 'webhook':
            config.endpoint = 'auto-detect';
            break;
          case 'scheduled':
            config.schedule = this.extractSchedule(input);
            break;
          default:
            config.manual_approval = true;
        }

        triggers.push({
          type: triggerType as 'codegen' | 'claude_code' | 'webhook' | 'manual' | 'scheduled',
          config
        });
      }
    }

    // Default to codegen if no specific triggers found and it's a development task
    if (triggers.length === 0 && this.isDevelopmentTask(input)) {
      triggers.push({
        type: 'codegen',
        config: { auto_trigger: false, review_required: true }
      });
    }

    return triggers;
  }

  private extractSchedule(input: string): string | undefined {
    const schedulePatterns = [
      /(?:every|each)\s+(\w+)/i,
      /(?:daily|weekly|monthly|hourly)/i,
      /(?:at\s+)?(\d{1,2}:\d{2})/i
    ];

    for (const pattern of schedulePatterns) {
      const match = input.match(pattern);
      if (match) {
        return match[0];
      }
    }

    return undefined;
  }

  private isDevelopmentTask(input: string): boolean {
    const devKeywords = [
      'code', 'implement', 'develop', 'build', 'create', 'function',
      'component', 'api', 'feature', 'bug', 'fix', 'refactor'
    ];
    
    const lowerInput = input.toLowerCase();
    return devKeywords.some(keyword => lowerInput.includes(keyword));
  }

  private splitIntoTaskSegments(input: string): string[] {
    // Split by common task separators
    const separators = [
      /\n\d+\.\s+/,  // Numbered lists
      /\n-\s+/,      // Bullet points
      /\n\*\s+/,     // Asterisk bullets
      /\n#{1,6}\s+/, // Markdown headers
      /\n\n+/        // Double newlines
    ];

    let segments = [input];
    
    for (const separator of separators) {
      const newSegments: string[] = [];
      for (const segment of segments) {
        newSegments.push(...segment.split(separator));
      }
      segments = newSegments;
    }

    return segments.filter(segment => segment.trim().length > 20);
  }

  private isValidTaskSegment(segment: string): boolean {
    const trimmed = segment.trim();
    
    // Must be long enough to be meaningful
    if (trimmed.length < 20) return false;
    
    // Should contain action words
    const actionWords = ['create', 'build', 'implement', 'fix', 'update', 'add', 'remove', 'modify'];
    const hasActionWord = actionWords.some(word => 
      trimmed.toLowerCase().includes(word)
    );
    
    return hasActionWord;
  }

  /**
   * Analyze task complexity based on multiple factors
   */
  analyzeTaskComplexity(requirement: ParsedRequirement): {
    score: number;
    factors: Record<string, number>;
    recommendation: string;
  } {
    const factors: Record<string, number> = {};
    
    // Description length factor
    factors.description_length = Math.min(requirement.description.length / 500, 1) * 20;
    
    // Technical requirements factor
    factors.technical_requirements = requirement.technical_requirements.length * 10;
    
    // Files to modify factor
    factors.files_to_modify = requirement.files_to_modify.length * 5;
    
    // Dependencies factor
    factors.dependencies = requirement.dependencies.length * 15;
    
    // Acceptance criteria factor
    factors.acceptance_criteria = requirement.acceptance_criteria.length * 8;
    
    // Workflow triggers factor
    factors.workflow_triggers = requirement.workflow_triggers.length * 12;
    
    const totalScore = Object.values(factors).reduce((sum, score) => sum + score, 0);
    
    let recommendation = 'simple';
    if (totalScore > 80) recommendation = 'epic';
    else if (totalScore > 50) recommendation = 'complex';
    else if (totalScore > 25) recommendation = 'moderate';
    
    return {
      score: totalScore,
      factors,
      recommendation
    };
  }
}

