"""
Factory classes for generating test task data.
"""
import factory
import factory.fuzzy
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import random


class TaskFactory(factory.Factory):
    """Factory for creating test task instances."""
    
    class Meta:
        model = dict  # Using dict as model for flexibility
    
    id = factory.Sequence(lambda n: f"task_{n:06d}")
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=500)
    status = factory.fuzzy.FuzzyChoice(['pending', 'in_progress', 'completed', 'failed', 'cancelled'])
    priority = factory.fuzzy.FuzzyInteger(1, 5)
    assignee_id = factory.Faker('uuid4')
    created_at = factory.Faker('date_time_between', start_date='-30d', end_date='now')
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at + timedelta(hours=random.randint(0, 72)))
    
    @factory.lazy_attribute
    def metadata(self):
        """Generate realistic task metadata."""
        return {
            'source': random.choice(['github', 'linear', 'manual', 'webhook']),
            'category': random.choice(['bug_fix', 'feature', 'improvement', 'documentation', 'testing']),
            'estimated_hours': random.randint(1, 40),
            'tags': random.sample(['urgent', 'backend', 'frontend', 'api', 'database', 'security'], k=random.randint(1, 3)),
            'repository': f"org/repo-{random.randint(1, 100)}",
            'branch': f"feature/task-{random.randint(1000, 9999)}"
        }


class CodeReviewTaskFactory(TaskFactory):
    """Factory for code review tasks."""
    
    title = factory.Faker('sentence', nb_words=3, variable_nb_words=False)
    status = factory.fuzzy.FuzzyChoice(['pending', 'in_progress', 'completed'])
    priority = factory.fuzzy.FuzzyInteger(2, 4)  # Medium priority range
    
    @factory.lazy_attribute
    def description(self):
        """Generate code review specific description."""
        templates = [
            "Review pull request #{pr_number} for {feature}",
            "Code review needed for {component} changes",
            "Security review required for {feature} implementation",
            "Performance review for {component} optimization"
        ]
        
        template = random.choice(templates)
        return template.format(
            pr_number=random.randint(1, 1000),
            feature=random.choice(['authentication', 'payment', 'user management', 'reporting']),
            component=random.choice(['API', 'database', 'frontend', 'backend'])
        )
    
    @factory.lazy_attribute
    def metadata(self):
        """Generate code review specific metadata."""
        base_metadata = super().metadata
        base_metadata.update({
            'category': 'code_review',
            'pr_number': random.randint(1, 1000),
            'files_changed': random.randint(1, 20),
            'lines_added': random.randint(10, 500),
            'lines_removed': random.randint(0, 200),
            'reviewers': [f"reviewer_{i}" for i in range(random.randint(1, 3))],
            'complexity_score': round(random.uniform(1.0, 10.0), 2)
        })
        return base_metadata


class BugFixTaskFactory(TaskFactory):
    """Factory for bug fix tasks."""
    
    status = factory.fuzzy.FuzzyChoice(['pending', 'in_progress', 'completed', 'failed'])
    priority = factory.fuzzy.FuzzyInteger(3, 5)  # Higher priority for bugs
    
    @factory.lazy_attribute
    def title(self):
        """Generate bug-specific titles."""
        bug_types = [
            "Fix {component} {issue}",
            "Resolve {severity} bug in {component}",
            "Address {issue} causing {impact}",
            "Hotfix for {component} {issue}"
        ]
        
        template = random.choice(bug_types)
        return template.format(
            component=random.choice(['API', 'UI', 'database', 'authentication', 'payment']),
            issue=random.choice(['crash', 'memory leak', 'timeout', 'validation error', 'race condition']),
            severity=random.choice(['critical', 'major', 'minor']),
            impact=random.choice(['data loss', 'service outage', 'performance degradation', 'user confusion'])
        )
    
    @factory.lazy_attribute
    def metadata(self):
        """Generate bug fix specific metadata."""
        base_metadata = super().metadata
        base_metadata.update({
            'category': 'bug_fix',
            'severity': random.choice(['critical', 'major', 'minor', 'trivial']),
            'bug_report_id': f"BUG-{random.randint(1000, 9999)}",
            'affected_users': random.randint(0, 10000),
            'reproduction_steps': [
                f"Step {i}: {action}" for i, action in enumerate(
                    random.sample([
                        'Navigate to login page',
                        'Enter invalid credentials',
                        'Click submit button',
                        'Observe error message',
                        'Check browser console',
                        'Verify database state'
                    ], k=random.randint(3, 5)
                ), 1)
            ],
            'error_logs': [
                f"ERROR: {error}" for error in random.sample([
                    'NullPointerException in UserService.authenticate()',
                    'Database connection timeout after 30s',
                    'Invalid JWT token signature',
                    'Rate limit exceeded for user',
                    'Memory allocation failed'
                ], k=random.randint(1, 3))
            ]
        })
        return base_metadata


class FeatureTaskFactory(TaskFactory):
    """Factory for feature development tasks."""
    
    status = factory.fuzzy.FuzzyChoice(['pending', 'in_progress', 'completed'])
    priority = factory.fuzzy.FuzzyInteger(1, 3)  # Lower priority for features
    
    @factory.lazy_attribute
    def title(self):
        """Generate feature-specific titles."""
        feature_templates = [
            "Implement {feature} for {component}",
            "Add {capability} to {system}",
            "Develop {feature} integration",
            "Create {component} {feature}"
        ]
        
        template = random.choice(feature_templates)
        return template.format(
            feature=random.choice(['OAuth integration', 'real-time notifications', 'data export', 'advanced search']),
            component=random.choice(['user dashboard', 'admin panel', 'API', 'mobile app']),
            capability=random.choice(['multi-factor authentication', 'file upload', 'batch processing']),
            system=random.choice(['payment system', 'notification service', 'user management'])
        )
    
    @factory.lazy_attribute
    def metadata(self):
        """Generate feature development specific metadata."""
        base_metadata = super().metadata
        base_metadata.update({
            'category': 'feature',
            'feature_flag': f"feature_{random.randint(1000, 9999)}",
            'acceptance_criteria': [
                f"AC{i}: {criteria}" for i, criteria in enumerate(
                    random.sample([
                        'User can successfully authenticate',
                        'System sends confirmation email',
                        'Data is validated before saving',
                        'Error messages are user-friendly',
                        'Performance meets SLA requirements',
                        'Feature works on mobile devices'
                    ], k=random.randint(3, 5)
                ), 1)
            ],
            'design_docs': [
                f"Design document: {doc}" for doc in random.sample([
                    'API specification',
                    'Database schema changes',
                    'UI/UX mockups',
                    'Security considerations',
                    'Performance requirements'
                ], k=random.randint(2, 4))
            ],
            'dependencies': [
                f"task_{random.randint(1, 1000):06d}" for _ in range(random.randint(0, 3))
            ]
        })
        return base_metadata


class WorkflowTaskFactory(TaskFactory):
    """Factory for workflow-related tasks."""
    
    @factory.lazy_attribute
    def metadata(self):
        """Generate workflow specific metadata."""
        base_metadata = super().metadata
        base_metadata.update({
            'workflow_id': f"wf_{random.randint(1000, 9999)}",
            'workflow_step': random.choice(['initialize', 'process', 'validate', 'deploy', 'cleanup']),
            'execution_context': {
                'trigger': random.choice(['webhook', 'manual', 'scheduled', 'api']),
                'environment': random.choice(['development', 'staging', 'production']),
                'version': f"v{random.randint(1, 10)}.{random.randint(0, 99)}.{random.randint(0, 99)}"
            },
            'retry_count': random.randint(0, 3),
            'timeout_seconds': random.choice([300, 600, 1800, 3600])
        })
        return base_metadata


class TaskBatchFactory:
    """Factory for creating batches of related tasks."""
    
    @staticmethod
    def create_sprint_tasks(sprint_name: str, task_count: int = 10) -> List[Dict]:
        """Create a batch of tasks for a sprint."""
        tasks = []
        
        # Create mix of different task types
        for i in range(task_count):
            if i < task_count * 0.4:  # 40% features
                task = FeatureTaskFactory()
            elif i < task_count * 0.7:  # 30% bug fixes
                task = BugFixTaskFactory()
            elif i < task_count * 0.9:  # 20% code reviews
                task = CodeReviewTaskFactory()
            else:  # 10% other tasks
                task = TaskFactory()
            
            # Add sprint metadata
            task['metadata']['sprint'] = sprint_name
            task['metadata']['sprint_week'] = random.randint(1, 2)
            
            tasks.append(task)
        
        return tasks
    
    @staticmethod
    def create_epic_tasks(epic_name: str, task_count: int = 15) -> List[Dict]:
        """Create a batch of tasks for an epic."""
        tasks = []
        epic_id = f"epic_{random.randint(1000, 9999)}"
        
        for i in range(task_count):
            # Mostly feature tasks for epics
            if i < task_count * 0.8:
                task = FeatureTaskFactory()
            else:
                task = TaskFactory()
            
            # Add epic metadata
            task['metadata']['epic'] = epic_name
            task['metadata']['epic_id'] = epic_id
            task['metadata']['epic_order'] = i + 1
            
            # Create dependencies between tasks
            if i > 0:
                task['metadata']['dependencies'] = [tasks[i-1]['id']]
            
            tasks.append(task)
        
        return tasks
    
    @staticmethod
    def create_release_tasks(release_version: str, task_count: int = 20) -> List[Dict]:
        """Create a batch of tasks for a release."""
        tasks = []
        
        # Create different phases of release tasks
        phases = ['development', 'testing', 'staging', 'production']
        tasks_per_phase = task_count // len(phases)
        
        for phase_idx, phase in enumerate(phases):
            for i in range(tasks_per_phase):
                if phase == 'development':
                    task = FeatureTaskFactory()
                elif phase == 'testing':
                    task = TaskFactory()
                    task['metadata']['category'] = 'testing'
                else:
                    task = TaskFactory()
                
                # Add release metadata
                task['metadata']['release'] = release_version
                task['metadata']['release_phase'] = phase
                task['metadata']['phase_order'] = i + 1
                
                # Set appropriate status based on phase
                if phase_idx == 0:  # Development phase
                    task['status'] = random.choice(['completed', 'in_progress'])
                elif phase_idx == 1:  # Testing phase
                    task['status'] = random.choice(['pending', 'in_progress'])
                else:  # Later phases
                    task['status'] = 'pending'
                
                tasks.append(task)
        
        return tasks


# Utility functions for test data generation
def generate_realistic_task_timeline(task: Dict) -> Dict:
    """Generate realistic timeline for a task."""
    created_at = task['created_at']
    
    if task['status'] == 'pending':
        # No updates yet
        task['updated_at'] = created_at
    elif task['status'] == 'in_progress':
        # Started recently
        task['updated_at'] = created_at + timedelta(hours=random.randint(1, 48))
        task['metadata']['started_at'] = task['updated_at'].isoformat()
    elif task['status'] in ['completed', 'failed']:
        # Has full timeline
        started_at = created_at + timedelta(hours=random.randint(1, 24))
        completed_at = started_at + timedelta(hours=random.randint(1, task['metadata']['estimated_hours'] * 2))
        
        task['updated_at'] = completed_at
        task['metadata']['started_at'] = started_at.isoformat()
        task['metadata']['completed_at'] = completed_at.isoformat()
        task['metadata']['actual_hours'] = round((completed_at - started_at).total_seconds() / 3600, 2)
    
    return task


def add_realistic_comments(task: Dict, comment_count: int = None) -> Dict:
    """Add realistic comments to a task."""
    if comment_count is None:
        comment_count = random.randint(0, 5)
    
    comments = []
    comment_templates = [
        "Started working on this task",
        "Encountered an issue with {component}",
        "Need clarification on {requirement}",
        "Progress update: {progress}% complete",
        "Blocked by {blocker}",
        "Ready for review",
        "Deployed to {environment}",
        "Task completed successfully"
    ]
    
    for i in range(comment_count):
        template = random.choice(comment_templates)
        comment = template.format(
            component=random.choice(['API', 'database', 'frontend', 'authentication']),
            requirement=random.choice(['acceptance criteria', 'business logic', 'UI design']),
            progress=random.randint(10, 90),
            blocker=random.choice(['dependency', 'external service', 'code review']),
            environment=random.choice(['staging', 'production', 'development'])
        )
        
        comment_time = task['created_at'] + timedelta(hours=random.randint(1, 72))
        
        comments.append({
            'id': f"comment_{random.randint(10000, 99999)}",
            'author': f"user_{random.randint(1, 100)}",
            'content': comment,
            'created_at': comment_time.isoformat()
        })
    
    task['comments'] = sorted(comments, key=lambda x: x['created_at'])
    return task


# Example usage
if __name__ == "__main__":
    # Create individual tasks
    basic_task = TaskFactory()
    code_review_task = CodeReviewTaskFactory()
    bug_fix_task = BugFixTaskFactory()
    feature_task = FeatureTaskFactory()
    
    print("Sample tasks created:")
    print(f"Basic task: {basic_task['title']}")
    print(f"Code review: {code_review_task['title']}")
    print(f"Bug fix: {bug_fix_task['title']}")
    print(f"Feature: {feature_task['title']}")
    
    # Create task batches
    sprint_tasks = TaskBatchFactory.create_sprint_tasks("Sprint 2024-Q1", 8)
    epic_tasks = TaskBatchFactory.create_epic_tasks("User Authentication Epic", 12)
    release_tasks = TaskBatchFactory.create_release_tasks("v2.1.0", 16)
    
    print(f"\nCreated {len(sprint_tasks)} sprint tasks")
    print(f"Created {len(epic_tasks)} epic tasks")
    print(f"Created {len(release_tasks)} release tasks")

