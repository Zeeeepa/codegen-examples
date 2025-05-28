"""
Claude API Client for Code Analysis and Fix Generation

Provides intelligent code analysis, error debugging, and fix suggestions
using Claude's advanced reasoning capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json
import aiohttp
from anthropic import AsyncAnthropic


@dataclass
class ClaudeResponse:
    """Response from Claude API with metadata."""
    content: str
    usage: Dict[str, int]
    model: str
    timestamp: float
    confidence: float = 1.0
    metadata: Dict[str, Any] = None


class ClaudeClient:
    """
    Advanced Claude API client for code analysis and validation.
    
    Features:
    - Intelligent code analysis and debugging
    - Context-aware fix suggestions
    - Rate limiting and retry logic
    - Streaming responses for large analyses
    - Custom prompt templates for different validation types
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        timeout: int = 60
    ):
        """Initialize Claude client with configuration."""
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self.rate_limit_requests = 50  # requests per minute
        self.rate_limit_tokens = 100000  # tokens per minute
        self.request_times = []
        self.token_usage = []
        
        # Prompt templates
        self.templates = {
            "code_analysis": self._load_template("code_analysis"),
            "error_debugging": self._load_template("error_debugging"),
            "fix_suggestion": self._load_template("fix_suggestion"),
            "security_review": self._load_template("security_review"),
            "performance_analysis": self._load_template("performance_analysis")
        }
    
    async def analyze_code(
        self,
        code: str,
        file_path: str,
        analysis_type: str = "general",
        context: Optional[Dict[str, Any]] = None
    ) -> ClaudeResponse:
        """
        Analyze code for issues, patterns, and improvements.
        
        Args:
            code: Source code to analyze
            file_path: Path to the file being analyzed
            analysis_type: Type of analysis (general, security, performance, etc.)
            context: Additional context for analysis
            
        Returns:
            ClaudeResponse with analysis results
        """
        prompt = self._build_analysis_prompt(code, file_path, analysis_type, context)
        return await self._make_request(prompt, "code_analysis")
    
    async def debug_error(
        self,
        error_message: str,
        code_context: str,
        stack_trace: Optional[str] = None,
        environment_info: Optional[Dict[str, Any]] = None
    ) -> ClaudeResponse:
        """
        Debug an error and provide detailed analysis.
        
        Args:
            error_message: The error message
            code_context: Relevant code context
            stack_trace: Stack trace if available
            environment_info: Environment and dependency information
            
        Returns:
            ClaudeResponse with debugging analysis
        """
        prompt = self._build_debug_prompt(error_message, code_context, stack_trace, environment_info)
        return await self._make_request(prompt, "error_debugging")
    
    async def suggest_fix(
        self,
        issue_description: str,
        code_context: str,
        file_path: str,
        similar_fixes: Optional[List[Dict[str, Any]]] = None
    ) -> ClaudeResponse:
        """
        Generate fix suggestions for identified issues.
        
        Args:
            issue_description: Description of the issue to fix
            code_context: Relevant code context
            file_path: Path to the file with the issue
            similar_fixes: Previously successful fixes for similar issues
            
        Returns:
            ClaudeResponse with fix suggestions
        """
        prompt = self._build_fix_prompt(issue_description, code_context, file_path, similar_fixes)
        return await self._make_request(prompt, "fix_suggestion")
    
    async def review_security(
        self,
        code: str,
        file_path: str,
        security_context: Optional[Dict[str, Any]] = None
    ) -> ClaudeResponse:
        """
        Perform security review of code.
        
        Args:
            code: Source code to review
            file_path: Path to the file being reviewed
            security_context: Security-specific context
            
        Returns:
            ClaudeResponse with security analysis
        """
        prompt = self._build_security_prompt(code, file_path, security_context)
        return await self._make_request(prompt, "security_review")
    
    async def analyze_performance(
        self,
        code: str,
        file_path: str,
        performance_data: Optional[Dict[str, Any]] = None
    ) -> ClaudeResponse:
        """
        Analyze code for performance issues and optimizations.
        
        Args:
            code: Source code to analyze
            file_path: Path to the file being analyzed
            performance_data: Performance metrics and profiling data
            
        Returns:
            ClaudeResponse with performance analysis
        """
        prompt = self._build_performance_prompt(code, file_path, performance_data)
        return await self._make_request(prompt, "performance_analysis")
    
    async def _make_request(
        self,
        prompt: str,
        request_type: str,
        stream: bool = False
    ) -> ClaudeResponse:
        """Make a request to Claude API with rate limiting and error handling."""
        await self._check_rate_limits()
        
        try:
            start_time = time.time()
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Track usage for rate limiting
            self.request_times.append(time.time())
            if hasattr(response, 'usage'):
                self.token_usage.append({
                    'timestamp': time.time(),
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                })
            
            # Calculate confidence based on response characteristics
            confidence = self._calculate_confidence(response, request_type)
            
            return ClaudeResponse(
                content=response.content[0].text,
                usage={
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                } if hasattr(response, 'usage') else {},
                model=self.model,
                timestamp=time.time(),
                confidence=confidence,
                metadata={
                    'request_type': request_type,
                    'response_time': time.time() - start_time
                }
            )
            
        except Exception as e:
            self.logger.error(f"Claude API request failed: {e}")
            raise
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits."""
        current_time = time.time()
        
        # Clean old request times (older than 1 minute)
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        self.token_usage = [u for u in self.token_usage if current_time - u['timestamp'] < 60]
        
        # Check request rate limit
        if len(self.request_times) >= self.rate_limit_requests:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                self.logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
        
        # Check token rate limit
        total_tokens = sum(u['input_tokens'] + u['output_tokens'] for u in self.token_usage)
        if total_tokens >= self.rate_limit_tokens:
            sleep_time = 60 - (current_time - self.token_usage[0]['timestamp'])
            if sleep_time > 0:
                self.logger.warning(f"Token rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
    
    def _calculate_confidence(self, response: Any, request_type: str) -> float:
        """Calculate confidence score for the response."""
        confidence = 1.0
        
        # Adjust confidence based on response length
        content_length = len(response.content[0].text)
        if content_length < 100:
            confidence *= 0.8
        elif content_length > 2000:
            confidence *= 0.9
        
        # Adjust confidence based on request type
        type_confidence = {
            "code_analysis": 0.9,
            "error_debugging": 0.85,
            "fix_suggestion": 0.8,
            "security_review": 0.95,
            "performance_analysis": 0.85
        }
        confidence *= type_confidence.get(request_type, 0.8)
        
        return min(1.0, max(0.0, confidence))
    
    def _build_analysis_prompt(
        self,
        code: str,
        file_path: str,
        analysis_type: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for code analysis."""
        base_prompt = f"""
You are an expert code reviewer and static analysis tool. Analyze the following code for issues, improvements, and best practices.

File: {file_path}
Analysis Type: {analysis_type}

Code:
```
{code}
```
"""
        
        if context:
            base_prompt += f"\nAdditional Context:\n{json.dumps(context, indent=2)}"
        
        base_prompt += """

Please provide a detailed analysis including:
1. Code quality issues (syntax, style, complexity)
2. Potential bugs or logical errors
3. Security vulnerabilities
4. Performance concerns
5. Best practice violations
6. Suggested improvements

Format your response as JSON with the following structure:
{
  "issues": [
    {
      "type": "issue_type",
      "severity": "critical|high|medium|low",
      "message": "description",
      "line": line_number,
      "suggestion": "how to fix"
    }
  ],
  "summary": "overall assessment",
  "confidence": 0.0-1.0
}
"""
        return base_prompt
    
    def _build_debug_prompt(
        self,
        error_message: str,
        code_context: str,
        stack_trace: Optional[str],
        environment_info: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for error debugging."""
        prompt = f"""
You are an expert debugger. Help analyze and debug the following error.

Error Message: {error_message}

Code Context:
```
{code_context}
```
"""
        
        if stack_trace:
            prompt += f"\nStack Trace:\n```\n{stack_trace}\n```"
        
        if environment_info:
            prompt += f"\nEnvironment Info:\n{json.dumps(environment_info, indent=2)}"
        
        prompt += """

Please provide:
1. Root cause analysis
2. Step-by-step debugging approach
3. Potential fixes
4. Prevention strategies

Format as JSON:
{
  "root_cause": "explanation",
  "debugging_steps": ["step1", "step2"],
  "fixes": [
    {
      "description": "fix description",
      "code_change": "specific code change",
      "confidence": 0.0-1.0
    }
  ],
  "prevention": "how to prevent similar issues"
}
"""
        return prompt
    
    def _build_fix_prompt(
        self,
        issue_description: str,
        code_context: str,
        file_path: str,
        similar_fixes: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Build prompt for fix suggestions."""
        prompt = f"""
You are an expert code fixer. Generate specific fix suggestions for the following issue.

Issue: {issue_description}
File: {file_path}

Code Context:
```
{code_context}
```
"""
        
        if similar_fixes:
            prompt += f"\nSimilar Successful Fixes:\n{json.dumps(similar_fixes, indent=2)}"
        
        prompt += """

Provide specific, actionable fixes:
1. Exact code changes needed
2. Alternative approaches
3. Testing recommendations
4. Potential side effects

Format as JSON:
{
  "fixes": [
    {
      "description": "what this fix does",
      "changes": [
        {
          "file": "file_path",
          "line": line_number,
          "old_code": "current code",
          "new_code": "fixed code"
        }
      ],
      "confidence": 0.0-1.0,
      "test_suggestions": ["test1", "test2"]
    }
  ]
}
"""
        return prompt
    
    def _build_security_prompt(
        self,
        code: str,
        file_path: str,
        security_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for security review."""
        prompt = f"""
You are a security expert. Perform a comprehensive security review of this code.

File: {file_path}

Code:
```
{code}
```
"""
        
        if security_context:
            prompt += f"\nSecurity Context:\n{json.dumps(security_context, indent=2)}"
        
        prompt += """

Analyze for:
1. Injection vulnerabilities (SQL, XSS, etc.)
2. Authentication/authorization issues
3. Data exposure risks
4. Cryptographic weaknesses
5. Input validation problems
6. OWASP Top 10 vulnerabilities

Format as JSON:
{
  "vulnerabilities": [
    {
      "type": "vulnerability_type",
      "severity": "critical|high|medium|low",
      "description": "detailed description",
      "location": "line_number or function",
      "impact": "potential impact",
      "remediation": "how to fix"
    }
  ],
  "security_score": 0-100,
  "recommendations": ["rec1", "rec2"]
}
"""
        return prompt
    
    def _build_performance_prompt(
        self,
        code: str,
        file_path: str,
        performance_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for performance analysis."""
        prompt = f"""
You are a performance optimization expert. Analyze this code for performance issues and improvements.

File: {file_path}

Code:
```
{code}
```
"""
        
        if performance_data:
            prompt += f"\nPerformance Data:\n{json.dumps(performance_data, indent=2)}"
        
        prompt += """

Analyze for:
1. Algorithmic complexity issues
2. Memory usage problems
3. I/O bottlenecks
4. Inefficient data structures
5. Unnecessary computations
6. Caching opportunities

Format as JSON:
{
  "performance_issues": [
    {
      "type": "issue_type",
      "severity": "critical|high|medium|low",
      "description": "issue description",
      "location": "line_number",
      "impact": "performance impact",
      "optimization": "suggested optimization"
    }
  ],
  "optimizations": [
    {
      "description": "optimization description",
      "expected_improvement": "percentage or description",
      "implementation": "how to implement"
    }
  ]
}
"""
        return prompt
    
    def _load_template(self, template_name: str) -> str:
        """Load prompt template from file or return default."""
        # In a real implementation, this would load from template files
        return f"Template for {template_name}"

