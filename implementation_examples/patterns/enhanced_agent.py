#!/usr/bin/env python
"""
Enhanced Agent Implementation Examples

This module demonstrates advanced integration patterns for the Codegen SDK,
including retry logic, connection pooling, batch processing, and observability.
"""

import asyncio
import time
import logging
from typing import List, Dict, Optional, Iterator, Any
from dataclasses import dataclass
from contextlib import contextmanager
import requests
from codegen import Agent, AgentTask


@dataclass
class TaskResult:
    """Enhanced task result with metadata"""
    task_id: str
    status: str
    result: str
    execution_time: float
    retry_count: int
    error: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker pattern for resilient agent calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                
                raise e
        
        return wrapper


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            if len(self.requests) >= self.requests_per_minute:
                sleep_time = 60 - (now - self.requests[0])
                time.sleep(sleep_time)
            
            self.requests.append(now)
            return func(*args, **kwargs)
        
        return wrapper


class EnhancedAgent:
    """Enhanced Agent with retry logic, circuit breaker, and observability"""
    
    def __init__(self, token: str, org_id: int, max_retries: int = 3):
        self.agent = Agent(token=token, org_id=org_id)
        self.max_retries = max_retries
        self.session = requests.Session()  # Connection pooling
        self.logger = logging.getLogger(__name__)
        
        # Initialize resilience patterns
        self.circuit_breaker = CircuitBreaker()
        self.rate_limiter = RateLimiter()
    
    @contextmanager
    def _trace_execution(self, operation: str, **metadata):
        """Context manager for tracing operations"""
        start_time = time.time()
        self.logger.info(f"Starting {operation}", extra=metadata)
        
        try:
            yield
            execution_time = time.time() - start_time
            self.logger.info(f"Completed {operation} in {execution_time:.2f}s", 
                           extra={**metadata, "execution_time": execution_time})
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Failed {operation} after {execution_time:.2f}s: {e}", 
                            extra={**metadata, "execution_time": execution_time, "error": str(e)})
            raise
    
    @circuit_breaker
    @rate_limiter
    def run_with_retry(self, prompt: str, context: Optional[Dict] = None) -> TaskResult:
        """Run agent task with retry logic and enhanced error handling"""
        
        retry_count = 0
        last_exception = None
        
        with self._trace_execution("agent_run", prompt_length=len(prompt)):
            for attempt in range(self.max_retries + 1):
                try:
                    start_time = time.time()
                    
                    # Enhance prompt with context if provided
                    enhanced_prompt = self._enhance_prompt(prompt, context)
                    
                    # Execute task
                    task = self.agent.run(enhanced_prompt)
                    result = self._wait_for_completion(task)
                    
                    execution_time = time.time() - start_time
                    
                    return TaskResult(
                        task_id=task.id,
                        status=task.status,
                        result=result,
                        execution_time=execution_time,
                        retry_count=retry_count
                    )
                
                except Exception as e:
                    retry_count += 1
                    last_exception = e
                    
                    if attempt < self.max_retries:
                        # Exponential backoff
                        sleep_time = 2 ** attempt
                        self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {sleep_time}s: {e}")
                        time.sleep(sleep_time)
                    else:
                        self.logger.error(f"All {self.max_retries + 1} attempts failed")
                        break
            
            # All retries exhausted
            return TaskResult(
                task_id="",
                status="failed",
                result="",
                execution_time=0,
                retry_count=retry_count,
                error=str(last_exception)
            )
    
    def _enhance_prompt(self, prompt: str, context: Optional[Dict]) -> str:
        """Enhance prompt with context information"""
        if not context:
            return prompt
        
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        return f"Context:\n{context_str}\n\nTask:\n{prompt}"
    
    def _wait_for_completion(self, task: AgentTask, timeout: int = 300) -> str:
        """Wait for task completion with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if task.status == "completed":
                return task.result
            elif task.status == "failed":
                raise Exception(f"Task failed: {task.result}")
            
            time.sleep(2)
            task.refresh()
        
        raise TimeoutError(f"Task {task.id} did not complete within {timeout} seconds")


class BatchProcessor:
    """Batch processing for multiple agent tasks"""
    
    def __init__(self, agent: EnhancedAgent, batch_size: int = 5, max_concurrent: int = 3):
        self.agent = agent
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(__name__)
    
    def process_batch(self, prompts: List[str], contexts: Optional[List[Dict]] = None) -> List[TaskResult]:
        """Process multiple prompts in batches"""
        if contexts and len(contexts) != len(prompts):
            raise ValueError("Contexts list must match prompts list length")
        
        results = []
        
        # Process in batches
        for i in range(0, len(prompts), self.batch_size):
            batch_prompts = prompts[i:i + self.batch_size]
            batch_contexts = contexts[i:i + self.batch_size] if contexts else [None] * len(batch_prompts)
            
            self.logger.info(f"Processing batch {i // self.batch_size + 1}, size: {len(batch_prompts)}")
            
            # Process batch concurrently (simulated with threading)
            batch_results = self._process_concurrent_batch(batch_prompts, batch_contexts)
            results.extend(batch_results)
        
        return results
    
    def _process_concurrent_batch(self, prompts: List[str], contexts: List[Optional[Dict]]) -> List[TaskResult]:
        """Process a batch of prompts concurrently"""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all tasks
            future_to_prompt = {
                executor.submit(self.agent.run_with_retry, prompt, context): (prompt, context)
                for prompt, context in zip(prompts, contexts)
            }
            
            results = []
            for future in concurrent.futures.as_completed(future_to_prompt):
                prompt, context = future_to_prompt[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to process prompt: {e}")
                    results.append(TaskResult(
                        task_id="",
                        status="failed",
                        result="",
                        execution_time=0,
                        retry_count=0,
                        error=str(e)
                    ))
            
            return results


class ContextManager:
    """Context management for maintaining conversation history"""
    
    def __init__(self, max_context_length: int = 10000):
        self.contexts = {}
        self.max_context_length = max_context_length
    
    def get_context(self, context_key: str) -> Dict:
        """Retrieve context for a given key"""
        return self.contexts.get(context_key, {})
    
    def update_context(self, context_key: str, prompt: str, result: str):
        """Update context with new interaction"""
        if context_key not in self.contexts:
            self.contexts[context_key] = {
                "history": [],
                "metadata": {}
            }
        
        # Add new interaction
        self.contexts[context_key]["history"].append({
            "prompt": prompt,
            "result": result,
            "timestamp": time.time()
        })
        
        # Trim context if too long
        self._trim_context(context_key)
    
    def _trim_context(self, context_key: str):
        """Trim context to stay within length limits"""
        context = self.contexts[context_key]
        history = context["history"]
        
        # Calculate total length
        total_length = sum(len(item["prompt"]) + len(item["result"]) for item in history)
        
        # Remove oldest entries if too long
        while total_length > self.max_context_length and len(history) > 1:
            removed = history.pop(0)
            total_length -= len(removed["prompt"]) + len(removed["result"])


class ContextualAgent:
    """Agent with context management capabilities"""
    
    def __init__(self, token: str, org_id: int):
        self.enhanced_agent = EnhancedAgent(token, org_id)
        self.context_manager = ContextManager()
    
    def run_with_context(self, prompt: str, context_key: str) -> TaskResult:
        """Run agent task with context awareness"""
        # Get existing context
        context = self.context_manager.get_context(context_key)
        
        # Add conversation history to context
        if context.get("history"):
            recent_history = context["history"][-3:]  # Last 3 interactions
            context["conversation_history"] = [
                f"Previous: {item['prompt']} -> {item['result'][:200]}..."
                for item in recent_history
            ]
        
        # Execute task
        result = self.enhanced_agent.run_with_retry(prompt, context)
        
        # Update context
        if result.status == "completed":
            self.context_manager.update_context(context_key, prompt, result.result)
        
        return result


# Example usage and demonstration
def main():
    """Demonstrate enhanced agent patterns"""
    import os
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize enhanced agent
    token = os.getenv("CODEGEN_TOKEN")
    if not token:
        print("Please set CODEGEN_TOKEN environment variable")
        return
    
    agent = EnhancedAgent(token=token, org_id=1)
    
    # Example 1: Single task with retry
    print("=== Example 1: Enhanced Single Task ===")
    result = agent.run_with_retry(
        "Create a Python function to calculate fibonacci numbers",
        context={"language": "python", "style": "functional"}
    )
    print(f"Result: {result.status}, Retries: {result.retry_count}")
    
    # Example 2: Batch processing
    print("\n=== Example 2: Batch Processing ===")
    batch_processor = BatchProcessor(agent, batch_size=3)
    
    prompts = [
        "Create a function to sort a list",
        "Create a function to find prime numbers",
        "Create a function to reverse a string"
    ]
    
    batch_results = batch_processor.process_batch(prompts)
    for i, result in enumerate(batch_results):
        print(f"Task {i+1}: {result.status} (Time: {result.execution_time:.2f}s)")
    
    # Example 3: Contextual conversation
    print("\n=== Example 3: Contextual Agent ===")
    contextual_agent = ContextualAgent(token=token, org_id=1)
    
    # First interaction
    result1 = contextual_agent.run_with_context(
        "Create a simple calculator class",
        context_key="calculator_project"
    )
    
    # Second interaction with context
    result2 = contextual_agent.run_with_context(
        "Add a method to calculate square root",
        context_key="calculator_project"
    )
    
    print(f"First task: {result1.status}")
    print(f"Second task: {result2.status}")


if __name__ == "__main__":
    main()

