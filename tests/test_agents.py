"""Tests for AI analysis agents."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.agents.style_agent import StyleAnalysisAgent
from app.agents.bug_agent import BugDetectionAgent
from app.agents.security_agent import SecurityAnalysisAgent
from app.agents.performance_agent import PerformanceAnalysisAgent


class TestStyleAnalysisAgent:
    """Test cases for style analysis agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a style analysis agent for testing."""
        return StyleAnalysisAgent()
    
    def test_system_prompt_contains_key_elements(self, agent):
        """Test that system prompt contains expected elements."""
        prompt = agent.get_system_prompt()
        assert "style" in prompt.lower()
        assert "formatting" in prompt.lower()
        assert "naming convention" in prompt.lower()
        assert "json" in prompt.lower()
    
    def test_analysis_prompt_template(self, agent):
        """Test analysis prompt template formatting."""
        template = agent.get_analysis_prompt()
        assert "{file_path}" in template
        assert "{file_content}" in template
        assert "{language}" in template
        assert "{file_diff}" in template
    
    @patch('app.agents.base_agent.ChatAnthropic')
    async def test_analyze_file(self, mock_llm_class, agent):
        """Test file analysis functionality."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '''
        {
            "issues": [
                {
                    "type": "style",
                    "line": 5,
                    "severity": "medium",
                    "description": "Line too long",
                    "suggestion": "Break line",
                    "confidence_score": 0.9
                }
            ]
        }
        '''
        
        mock_llm = Mock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_class.return_value = mock_llm
        
        # Create agent with mocked LLM
        agent = StyleAnalysisAgent()
        
        # Test analysis
        result = await agent.analyze_file(
            file_path="test.py",
            file_content="def very_long_function_name():\n    pass",
            language="python"
        )
        
        assert result.file_path == "test.py"
        assert len(result.issues) == 1
        assert result.issues[0].type == "style"
        assert result.issues[0].line == 5


class TestBugDetectionAgent:
    """Test cases for bug detection agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a bug detection agent for testing."""
        return BugDetectionAgent()
    
    def test_system_prompt_contains_bug_patterns(self, agent):
        """Test that system prompt mentions bug patterns."""
        prompt = agent.get_system_prompt()
        assert "null pointer" in prompt.lower()
        assert "exception" in prompt.lower()
        assert "bug" in prompt.lower()


class TestSecurityAnalysisAgent:
    """Test cases for security analysis agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a security analysis agent for testing."""
        return SecurityAnalysisAgent()
    
    def test_system_prompt_contains_security_issues(self, agent):
        """Test that system prompt mentions security issues."""
        prompt = agent.get_system_prompt()
        assert "sql injection" in prompt.lower()
        assert "xss" in prompt.lower()
        assert "owasp" in prompt.lower()
        assert "vulnerability" in prompt.lower()


class TestPerformanceAnalysisAgent:
    """Test cases for performance analysis agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a performance analysis agent for testing."""
        return PerformanceAnalysisAgent()
    
    def test_system_prompt_contains_performance_issues(self, agent):
        """Test that system prompt mentions performance issues."""
        prompt = agent.get_system_prompt()
        assert "performance" in prompt.lower()
        assert "optimization" in prompt.lower()
        assert "complexity" in prompt.lower()
        assert "bottleneck" in prompt.lower()