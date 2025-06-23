"""
MCP Context Manager for Phase 4 Implementation
=============================================

This module provides context awareness and real-time monitoring
for the ViolentUTF MCP integration.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import json

logger = logging.getLogger(__name__)

class ConversationContext:
    """Manages conversation context and metadata"""
    
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.turns: deque = deque(maxlen=max_turns)
        self.metadata: Dict[str, Any] = {}
        self.active_resources: List[str] = []
        self.test_results: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a conversation turn"""
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.turns.append(turn)
        self.updated_at = datetime.now()
    
    def get_recent_turns(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation turns"""
        return list(self.turns)[-count:]
    
    def add_resource(self, resource_uri: str):
        """Track active resource"""
        if resource_uri not in self.active_resources:
            self.active_resources.append(resource_uri)
            self.updated_at = datetime.now()
    
    def add_test_result(self, test_type: str, result: Any):
        """Add test result to context"""
        self.test_results.append({
            "type": test_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context"""
        return {
            "turn_count": len(self.turns),
            "active_resources": len(self.active_resources),
            "test_results": len(self.test_results),
            "duration": (datetime.now() - self.created_at).total_seconds(),
            "last_activity": self.updated_at.isoformat()
        }
    
    def extract_topics(self) -> List[str]:
        """Extract main topics from conversation"""
        topics = set()
        
        # Simple keyword extraction
        keywords = {
            "security": ["security", "secure", "vulnerability", "exploit"],
            "jailbreak": ["jailbreak", "bypass", "override", "ignore"],
            "bias": ["bias", "biased", "fair", "discriminate"],
            "privacy": ["privacy", "private", "personal", "data"],
            "testing": ["test", "testing", "evaluate", "assess"],
            "prompt": ["prompt", "enhance", "improve", "optimize"]
        }
        
        # Check recent turns
        for turn in list(self.turns)[-10:]:
            content_lower = turn["content"].lower()
            for topic, words in keywords.items():
                if any(word in content_lower for word in words):
                    topics.add(topic)
        
        return list(topics)

class ContextAwareMonitor:
    """Monitors conversation and provides real-time insights"""
    
    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.suggestions_queue: deque = deque(maxlen=10)
        self._callbacks: Dict[str, List[Callable]] = {
            "context_update": [],
            "alert": [],
            "suggestion": []
        }
    
    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """Get or create context for session"""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext()
        return self.contexts[session_id]
    
    def analyze_conversation(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """Analyze conversation and provide insights"""
        context = self.get_or_create_context(session_id)
        
        # Add user turn
        context.add_turn("user", user_input)
        
        # Extract insights
        insights = {
            "topics": context.extract_topics(),
            "suggestions": [],
            "alerts": [],
            "context_summary": context.get_context_summary()
        }
        
        # Check for security concerns
        security_patterns = [
            ("jailbreak", ["ignore", "bypass", "override", "forget"]),
            ("injection", ["system:", "admin:", "execute", "eval"]),
            ("data_leak", ["password", "api key", "secret", "credential"])
        ]
        
        user_input_lower = user_input.lower()
        for concern, patterns in security_patterns:
            if any(pattern in user_input_lower for pattern in patterns):
                alert = {
                    "type": "security",
                    "concern": concern,
                    "severity": "medium",
                    "message": f"Potential {concern} attempt detected",
                    "timestamp": datetime.now().isoformat()
                }
                insights["alerts"].append(alert)
                self._trigger_alert(alert)
        
        # Generate contextual suggestions
        suggestions = self._generate_suggestions(context, user_input)
        insights["suggestions"] = suggestions
        
        # Trigger callbacks
        self._trigger_context_update(session_id, insights)
        
        return insights
    
    def _generate_suggestions(self, context: ConversationContext, user_input: str) -> List[Dict[str, Any]]:
        """Generate contextual suggestions"""
        suggestions = []
        
        # Based on topics
        topics = context.extract_topics()
        
        if "security" in topics and "testing" not in topics:
            suggestions.append({
                "type": "action",
                "text": "Run security analysis on recent prompts",
                "command": "/mcp analyze",
                "reason": "Security topics discussed but no testing performed"
            })
        
        if "jailbreak" in topics:
            suggestions.append({
                "type": "resource",
                "text": "Load jailbreak testing dataset",
                "command": "/mcp dataset jailbreak-patterns",
                "reason": "Jailbreak testing context detected"
            })
        
        if len(context.turns) > 10 and not context.test_results:
            suggestions.append({
                "type": "test",
                "text": "Generate test suite for conversation",
                "command": "/mcp test comprehensive",
                "reason": "Long conversation without testing"
            })
        
        # Add to queue and trigger callbacks
        for suggestion in suggestions:
            self.suggestions_queue.append(suggestion)
            self._trigger_suggestion(suggestion)
        
        return suggestions
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for events"""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
    
    def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger alert callbacks"""
        self.alerts.append(alert)
        for callback in self._callbacks["alert"]:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def _trigger_suggestion(self, suggestion: Dict[str, Any]):
        """Trigger suggestion callbacks"""
        for callback in self._callbacks["suggestion"]:
            try:
                callback(suggestion)
            except Exception as e:
                logger.error(f"Suggestion callback error: {e}")
    
    def _trigger_context_update(self, session_id: str, insights: Dict[str, Any]):
        """Trigger context update callbacks"""
        for callback in self._callbacks["context_update"]:
            try:
                callback(session_id, insights)
            except Exception as e:
                logger.error(f"Context update callback error: {e}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        context = self.contexts.get(session_id)
        if not context:
            return {}
        
        return {
            "summary": context.get_context_summary(),
            "topics": context.extract_topics(),
            "resources": context.active_resources,
            "test_count": len(context.test_results),
            "alerts": [a for a in self.alerts if a.get("session_id") == session_id]
        }

class ResourceMonitor:
    """Monitors MCP resources and provides updates"""
    
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.resource_cache: Dict[str, Any] = {}
        self.subscriptions: Dict[str, List[Callable]] = {}
        self._monitoring = False
        self._monitor_task = None
    
    async def start_monitoring(self, interval: int = 5):
        """Start resource monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("Resource monitoring started")
    
    async def stop_monitoring(self):
        """Stop resource monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                # Check for resource updates
                await self._check_resources()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(interval)
    
    async def _check_resources(self):
        """Check resources for updates"""
        try:
            # Get current resources
            resources = await self.mcp_client.list_resources()
            
            # Check for changes
            for resource in resources:
                uri = resource.uri
                
                # Check if resource changed
                if uri in self.resource_cache:
                    # Simple change detection (would be more sophisticated in production)
                    if self._has_changed(resource, self.resource_cache[uri]):
                        await self._notify_subscribers(uri, resource)
                
                # Update cache
                self.resource_cache[uri] = resource
        
        except Exception as e:
            logger.error(f"Resource check error: {e}")
    
    def _has_changed(self, new_resource, cached_resource) -> bool:
        """Check if resource has changed"""
        # Simple comparison - in production would use proper change detection
        return str(new_resource) != str(cached_resource)
    
    async def _notify_subscribers(self, uri: str, resource: Any):
        """Notify subscribers of resource change"""
        if uri in self.subscriptions:
            for callback in self.subscriptions[uri]:
                try:
                    await callback(uri, resource)
                except Exception as e:
                    logger.error(f"Subscriber notification error: {e}")
    
    def subscribe(self, uri: str, callback: Callable):
        """Subscribe to resource updates"""
        if uri not in self.subscriptions:
            self.subscriptions[uri] = []
        self.subscriptions[uri].append(callback)
        logger.info(f"Subscribed to resource: {uri}")
    
    def unsubscribe(self, uri: str, callback: Callable):
        """Unsubscribe from resource updates"""
        if uri in self.subscriptions and callback in self.subscriptions[uri]:
            self.subscriptions[uri].remove(callback)
            if not self.subscriptions[uri]:
                del self.subscriptions[uri]
            logger.info(f"Unsubscribed from resource: {uri}")

class IntegratedContextManager:
    """Integrates context awareness with MCP operations"""
    
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.monitor = ContextAwareMonitor()
        self.resource_monitor = ResourceMonitor(mcp_client)
        
        # Register internal callbacks
        self.monitor.register_callback("suggestion", self._handle_suggestion)
        self.monitor.register_callback("alert", self._handle_alert)
    
    def _handle_suggestion(self, suggestion: Dict[str, Any]):
        """Handle generated suggestions"""
        logger.info(f"Suggestion generated: {suggestion['text']}")
    
    def _handle_alert(self, alert: Dict[str, Any]):
        """Handle security alerts"""
        logger.warning(f"Security alert: {alert['message']}")
    
    def process_input(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """Process user input with context awareness"""
        # Analyze conversation
        insights = self.monitor.analyze_conversation(session_id, user_input)
        
        # Get session context
        context = self.monitor.get_or_create_context(session_id)
        
        # Enhance insights with context
        insights["active_resources"] = context.active_resources
        insights["recent_tests"] = context.test_results[-3:] if context.test_results else []
        
        return insights
    
    def track_command_execution(self, session_id: str, command: str, result: Any):
        """Track command execution in context"""
        context = self.monitor.get_or_create_context(session_id)
        
        # Add as conversation turn
        context.add_turn("system", f"Executed: {command}", {
            "command": command,
            "success": result.get("success", True) if isinstance(result, dict) else True
        })
        
        # Track specific results
        if "test" in command:
            context.add_test_result(command, result)
        elif "dataset" in command and isinstance(result, dict):
            if result.get("type") == "dataset_loaded":
                context.add_resource(f"dataset:{result.get('name', 'unknown')}")
    
    def get_contextual_help(self, session_id: str) -> List[Dict[str, Any]]:
        """Get contextual help based on current session"""
        context = self.monitor.get_or_create_context(session_id)
        topics = context.extract_topics()
        
        help_items = []
        
        if "security" in topics:
            help_items.append({
                "title": "Security Testing Guide",
                "content": "Use `/mcp test security` to run comprehensive security tests",
                "link": "/docs/security-testing"
            })
        
        if "jailbreak" in topics:
            help_items.append({
                "title": "Jailbreak Prevention",
                "content": "Try `/mcp analyze` to detect potential vulnerabilities",
                "link": "/docs/jailbreak-prevention"
            })
        
        if not context.test_results:
            help_items.append({
                "title": "Getting Started with Testing",
                "content": "Begin with `/mcp test` to generate test variations",
                "link": "/docs/getting-started"
            })
        
        return help_items
    
    async def start_monitoring(self):
        """Start resource monitoring"""
        await self.resource_monitor.start_monitoring()
    
    async def stop_monitoring(self):
        """Stop resource monitoring"""
        await self.resource_monitor.stop_monitoring()

# Global context manager instance (initialized in UI)
context_manager: Optional[IntegratedContextManager] = None