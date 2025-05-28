import { Graph, alg } from 'graphlib';
import { z } from 'zod';
import { logger } from './utils/logger.js';
import { Task, TaskDependency } from './database-client.js';

export const DependencyAnalysisSchema = z.object({
  hasCycles: z.boolean(),
  cycles: z.array(z.array(z.string())),
  criticalPath: z.array(z.string()),
  parallelizable: z.array(z.array(z.string())),
  bottlenecks: z.array(z.string()),
  estimatedDuration: z.number(),
  riskFactors: z.array(z.object({
    type: z.string(),
    severity: z.enum(['low', 'medium', 'high', 'critical']),
    description: z.string(),
    affectedTasks: z.array(z.string())
  }))
});

export type DependencyAnalysis = z.infer<typeof DependencyAnalysisSchema>;

export interface TaskNode {
  id: string;
  title: string;
  status: string;
  priority: string;
  complexity: string;
  estimatedHours?: number;
  assignee?: string;
}

export interface DependencyEdge {
  from: string;
  to: string;
  type: string;
  weight?: number;
}

export class DependencyAnalyzer {
  private graph: Graph;

  constructor() {
    this.graph = new Graph({ directed: true });
  }

  /**
   * Build dependency graph from tasks and dependencies
   */
  buildGraph(tasks: Task[], dependencies: TaskDependency[]): void {
    logger.info('Building dependency graph', { 
      taskCount: tasks.length, 
      dependencyCount: dependencies.length 
    });

    // Clear existing graph
    this.graph = new Graph({ directed: true });

    // Add nodes (tasks)
    tasks.forEach(task => {
      this.graph.setNode(task.id, {
        id: task.id,
        title: task.title,
        status: task.status,
        priority: task.priority,
        complexity: task.complexity,
        estimatedHours: task.estimated_hours,
        assignee: task.assignee
      } as TaskNode);
    });

    // Add edges (dependencies)
    dependencies.forEach(dep => {
      // Edge goes from dependency to dependent task
      // (task depends on dependency, so dependency must complete first)
      this.graph.setEdge(dep.depends_on_task_id, dep.task_id, {
        from: dep.depends_on_task_id,
        to: dep.task_id,
        type: dep.dependency_type,
        weight: this.calculateDependencyWeight(dep.dependency_type)
      } as DependencyEdge);
    });

    logger.info('Dependency graph built successfully', {
      nodes: this.graph.nodeCount(),
      edges: this.graph.edgeCount()
    });
  }

  /**
   * Perform comprehensive dependency analysis
   */
  analyze(): DependencyAnalysis {
    logger.info('Starting dependency analysis');

    const analysis: DependencyAnalysis = {
      hasCycles: false,
      cycles: [],
      criticalPath: [],
      parallelizable: [],
      bottlenecks: [],
      estimatedDuration: 0,
      riskFactors: []
    };

    try {
      // Check for cycles
      const cycles = this.detectCycles();
      analysis.hasCycles = cycles.length > 0;
      analysis.cycles = cycles;

      // Find critical path
      analysis.criticalPath = this.findCriticalPath();

      // Identify parallelizable tasks
      analysis.parallelizable = this.findParallelizableTasks();

      // Identify bottlenecks
      analysis.bottlenecks = this.identifyBottlenecks();

      // Calculate estimated duration
      analysis.estimatedDuration = this.calculateEstimatedDuration();

      // Assess risk factors
      analysis.riskFactors = this.assessRiskFactors();

      logger.info('Dependency analysis completed', {
        hasCycles: analysis.hasCycles,
        criticalPathLength: analysis.criticalPath.length,
        parallelGroups: analysis.parallelizable.length,
        bottlenecks: analysis.bottlenecks.length,
        estimatedDuration: analysis.estimatedDuration
      });

      return DependencyAnalysisSchema.parse(analysis);
    } catch (error) {
      logger.error('Dependency analysis failed', { error });
      throw new Error(`Dependency analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Detect circular dependencies using DFS
   */
  private detectCycles(): string[][] {
    const cycles: string[][] = [];
    
    try {
      // Use graphlib's built-in cycle detection
      const isAcyclic = alg.isAcyclic(this.graph);
      
      if (!isAcyclic) {
        // Find all strongly connected components
        const components = alg.tarjan(this.graph);
        
        // Filter components with more than one node (cycles)
        components.forEach(component => {
          if (component.length > 1) {
            cycles.push(component);
          }
        });
      }
    } catch (error) {
      logger.error('Cycle detection failed', { error });
    }

    return cycles;
  }

  /**
   * Find the critical path (longest path through the graph)
   */
  private findCriticalPath(): string[] {
    try {
      // Topological sort to get a valid ordering
      const sorted = alg.topsort(this.graph);
      
      if (!sorted || sorted.length === 0) {
        return [];
      }

      // Calculate longest path using dynamic programming
      const distances: Record<string, number> = {};
      const predecessors: Record<string, string | null> = {};

      // Initialize distances
      sorted.forEach(nodeId => {
        distances[nodeId] = 0;
        predecessors[nodeId] = null;
      });

      // Calculate longest distances
      sorted.forEach(nodeId => {
        const node = this.graph.node(nodeId) as TaskNode;
        const nodeWeight = node.estimatedHours || this.getDefaultEstimate(node.complexity);

        this.graph.successors(nodeId)?.forEach(successorId => {
          const newDistance = distances[nodeId] + nodeWeight;
          if (newDistance > distances[successorId]) {
            distances[successorId] = newDistance;
            predecessors[successorId] = nodeId;
          }
        });
      });

      // Find the node with maximum distance
      let maxDistance = 0;
      let endNode = '';
      
      Object.entries(distances).forEach(([nodeId, distance]) => {
        if (distance > maxDistance) {
          maxDistance = distance;
          endNode = nodeId;
        }
      });

      // Reconstruct the critical path
      const path: string[] = [];
      let current: string | null = endNode;
      
      while (current) {
        path.unshift(current);
        current = predecessors[current];
      }

      return path;
    } catch (error) {
      logger.error('Critical path calculation failed', { error });
      return [];
    }
  }

  /**
   * Find groups of tasks that can be executed in parallel
   */
  private findParallelizableTasks(): string[][] {
    try {
      const parallelGroups: string[][] = [];
      const visited = new Set<string>();
      
      // Get topological ordering
      const sorted = alg.topsort(this.graph);
      
      if (!sorted) {
        return [];
      }

      // Group tasks by their level in the dependency hierarchy
      const levels: Record<number, string[]> = {};
      const nodeLevels: Record<string, number> = {};

      // Calculate level for each node
      sorted.forEach(nodeId => {
        let level = 0;
        
        // Find the maximum level of all predecessors
        this.graph.predecessors(nodeId)?.forEach(predId => {
          if (nodeLevels[predId] !== undefined) {
            level = Math.max(level, nodeLevels[predId] + 1);
          }
        });

        nodeLevels[nodeId] = level;
        
        if (!levels[level]) {
          levels[level] = [];
        }
        levels[level].push(nodeId);
      });

      // Convert levels to parallel groups (filter out single-task levels)
      Object.values(levels).forEach(levelTasks => {
        if (levelTasks.length > 1) {
          parallelGroups.push(levelTasks);
        }
      });

      return parallelGroups;
    } catch (error) {
      logger.error('Parallelizable task detection failed', { error });
      return [];
    }
  }

  /**
   * Identify bottleneck tasks (high in-degree or out-degree)
   */
  private identifyBottlenecks(): string[] {
    const bottlenecks: string[] = [];
    const threshold = 3; // Tasks with more than 3 dependencies/dependents

    try {
      this.graph.nodes().forEach(nodeId => {
        const inDegree = this.graph.predecessors(nodeId)?.length || 0;
        const outDegree = this.graph.successors(nodeId)?.length || 0;
        
        if (inDegree >= threshold || outDegree >= threshold) {
          bottlenecks.push(nodeId);
        }
      });
    } catch (error) {
      logger.error('Bottleneck identification failed', { error });
    }

    return bottlenecks;
  }

  /**
   * Calculate estimated total duration considering parallelization
   */
  private calculateEstimatedDuration(): number {
    try {
      const criticalPath = this.findCriticalPath();
      let totalDuration = 0;

      criticalPath.forEach(nodeId => {
        const node = this.graph.node(nodeId) as TaskNode;
        totalDuration += node.estimatedHours || this.getDefaultEstimate(node.complexity);
      });

      return totalDuration;
    } catch (error) {
      logger.error('Duration calculation failed', { error });
      return 0;
    }
  }

  /**
   * Assess various risk factors in the dependency graph
   */
  private assessRiskFactors(): Array<{
    type: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    affectedTasks: string[];
  }> {
    const risks: Array<{
      type: string;
      severity: 'low' | 'medium' | 'high' | 'critical';
      description: string;
      affectedTasks: string[];
    }> = [];

    try {
      // Check for circular dependencies
      const cycles = this.detectCycles();
      if (cycles.length > 0) {
        cycles.forEach(cycle => {
          risks.push({
            type: 'circular_dependency',
            severity: 'critical',
            description: `Circular dependency detected involving ${cycle.length} tasks`,
            affectedTasks: cycle
          });
        });
      }

      // Check for single points of failure
      const bottlenecks = this.identifyBottlenecks();
      bottlenecks.forEach(bottleneck => {
        const node = this.graph.node(bottleneck) as TaskNode;
        const dependentCount = this.graph.successors(bottleneck)?.length || 0;
        
        if (dependentCount > 5) {
          risks.push({
            type: 'single_point_of_failure',
            severity: 'high',
            description: `Task "${node.title}" blocks ${dependentCount} other tasks`,
            affectedTasks: [bottleneck, ...(this.graph.successors(bottleneck) || [])]
          });
        }
      });

      // Check for unassigned critical path tasks
      const criticalPath = this.findCriticalPath();
      const unassignedCritical = criticalPath.filter(nodeId => {
        const node = this.graph.node(nodeId) as TaskNode;
        return !node.assignee;
      });

      if (unassignedCritical.length > 0) {
        risks.push({
          type: 'unassigned_critical_tasks',
          severity: 'medium',
          description: `${unassignedCritical.length} critical path tasks are unassigned`,
          affectedTasks: unassignedCritical
        });
      }

      // Check for high complexity tasks without estimates
      this.graph.nodes().forEach(nodeId => {
        const node = this.graph.node(nodeId) as TaskNode;
        if ((node.complexity === 'complex' || node.complexity === 'epic') && !node.estimatedHours) {
          risks.push({
            type: 'missing_estimates',
            severity: 'medium',
            description: `High complexity task "${node.title}" lacks time estimate`,
            affectedTasks: [nodeId]
          });
        }
      });

      // Check for long dependency chains
      const maxChainLength = this.findLongestDependencyChain();
      if (maxChainLength > 10) {
        risks.push({
          type: 'long_dependency_chain',
          severity: 'medium',
          description: `Dependency chain of ${maxChainLength} tasks may cause delays`,
          affectedTasks: this.findCriticalPath()
        });
      }

    } catch (error) {
      logger.error('Risk assessment failed', { error });
    }

    return risks;
  }

  /**
   * Find the longest dependency chain in the graph
   */
  private findLongestDependencyChain(): number {
    try {
      const sorted = alg.topsort(this.graph);
      if (!sorted) return 0;

      const depths: Record<string, number> = {};

      // Initialize depths
      sorted.forEach(nodeId => {
        depths[nodeId] = 0;
      });

      // Calculate maximum depth for each node
      sorted.forEach(nodeId => {
        this.graph.successors(nodeId)?.forEach(successorId => {
          depths[successorId] = Math.max(depths[successorId], depths[nodeId] + 1);
        });
      });

      return Math.max(...Object.values(depths));
    } catch (error) {
      logger.error('Longest chain calculation failed', { error });
      return 0;
    }
  }

  /**
   * Get default time estimate based on complexity
   */
  private getDefaultEstimate(complexity: string): number {
    const estimates = {
      simple: 2,
      moderate: 8,
      complex: 24,
      epic: 80
    };
    return estimates[complexity as keyof typeof estimates] || 8;
  }

  /**
   * Calculate weight for dependency edge based on type
   */
  private calculateDependencyWeight(dependencyType: string): number {
    const weights = {
      blocks: 1.0,      // Hard dependency
      requires: 0.8,    // Soft dependency
      suggests: 0.3     // Optional dependency
    };
    return weights[dependencyType as keyof typeof weights] || 1.0;
  }

  /**
   * Get tasks that are ready to start (no incomplete dependencies)
   */
  getReadyTasks(): string[] {
    const readyTasks: string[] = [];

    try {
      this.graph.nodes().forEach(nodeId => {
        const node = this.graph.node(nodeId) as TaskNode;
        
        // Skip if task is already completed or in progress
        if (node.status === 'completed' || node.status === 'in_progress') {
          return;
        }

        // Check if all dependencies are completed
        const dependencies = this.graph.predecessors(nodeId) || [];
        const allDependenciesComplete = dependencies.every(depId => {
          const depNode = this.graph.node(depId) as TaskNode;
          return depNode.status === 'completed';
        });

        if (allDependenciesComplete) {
          readyTasks.push(nodeId);
        }
      });
    } catch (error) {
      logger.error('Ready tasks calculation failed', { error });
    }

    return readyTasks;
  }

  /**
   * Suggest optimal task ordering for execution
   */
  suggestTaskOrdering(): string[] {
    try {
      // Start with topological sort
      const baseOrder = alg.topsort(this.graph);
      if (!baseOrder) return [];

      // Enhance ordering with priority and complexity considerations
      const enhancedOrder = baseOrder.sort((a, b) => {
        const nodeA = this.graph.node(a) as TaskNode;
        const nodeB = this.graph.node(b) as TaskNode;

        // Priority weights
        const priorityWeights = { critical: 4, high: 3, medium: 2, low: 1 };
        const priorityA = priorityWeights[nodeA.priority as keyof typeof priorityWeights] || 2;
        const priorityB = priorityWeights[nodeB.priority as keyof typeof priorityWeights] || 2;

        // Complexity weights (simpler tasks first for quick wins)
        const complexityWeights = { simple: 4, moderate: 3, complex: 2, epic: 1 };
        const complexityA = complexityWeights[nodeA.complexity as keyof typeof complexityWeights] || 3;
        const complexityB = complexityWeights[nodeB.complexity as keyof typeof complexityWeights] || 3;

        // Combined score (higher is better)
        const scoreA = priorityA * 0.6 + complexityA * 0.4;
        const scoreB = priorityB * 0.6 + complexityB * 0.4;

        return scoreB - scoreA;
      });

      return enhancedOrder;
    } catch (error) {
      logger.error('Task ordering suggestion failed', { error });
      return [];
    }
  }

  /**
   * Export graph data for visualization
   */
  exportGraphData(): {
    nodes: Array<TaskNode & { level: number }>;
    edges: DependencyEdge[];
  } {
    const nodes: Array<TaskNode & { level: number }> = [];
    const edges: DependencyEdge[] = [];

    try {
      // Calculate levels for visualization
      const sorted = alg.topsort(this.graph);
      const nodeLevels: Record<string, number> = {};

      if (sorted) {
        sorted.forEach(nodeId => {
          let level = 0;
          this.graph.predecessors(nodeId)?.forEach(predId => {
            if (nodeLevels[predId] !== undefined) {
              level = Math.max(level, nodeLevels[predId] + 1);
            }
          });
          nodeLevels[nodeId] = level;
        });
      }

      // Export nodes
      this.graph.nodes().forEach(nodeId => {
        const node = this.graph.node(nodeId) as TaskNode;
        nodes.push({
          ...node,
          level: nodeLevels[nodeId] || 0
        });
      });

      // Export edges
      this.graph.edges().forEach(edge => {
        const edgeData = this.graph.edge(edge) as DependencyEdge;
        edges.push(edgeData);
      });

    } catch (error) {
      logger.error('Graph export failed', { error });
    }

    return { nodes, edges };
  }
}

