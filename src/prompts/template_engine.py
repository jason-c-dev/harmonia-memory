"""
Template engine for prompt rendering with context injection.
"""
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .types import PromptContext, MemoryType, ExtractionMode


class PromptTemplate:
    """A prompt template with variable substitution and conditional rendering."""
    
    def __init__(self, template_text: str, name: str = "", version: str = "1.0"):
        """
        Initialize prompt template.
        
        Args:
            template_text: Template text with variables like {{variable_name}}
            name: Template name for identification
            version: Template version
        """
        self.template_text = template_text
        self.name = name
        self.version = version
        self.variables = self._extract_variables()
    
    def _extract_variables(self) -> List[str]:
        """Extract variable names from template."""
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, self.template_text)))
    
    def render(self, context: Dict[str, Any]) -> str:
        """
        Render template with provided context.
        
        Args:
            context: Dictionary of variables to substitute
            
        Returns:
            Rendered template text
        """
        rendered = self.template_text
        
        # Handle conditional blocks first
        rendered = self._process_conditionals(rendered, context)
        
        # Substitute variables
        for var in self.variables:
            placeholder = f"{{{{{var}}}}}"
            value = context.get(var, f"[MISSING:{var}]")
            
            # Convert complex objects to strings
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            elif not isinstance(value, str):
                value = str(value)
                
            rendered = rendered.replace(placeholder, value)
        
        return rendered.strip()
    
    def _process_conditionals(self, text: str, context: Dict[str, Any]) -> str:
        """Process conditional blocks in template."""
        # Handle {{#if variable}} ... {{/if}} blocks
        if_pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
        
        def replace_if(match):
            var_name = match.group(1)
            content = match.group(2)
            if context.get(var_name):
                return content
            return ""
        
        text = re.sub(if_pattern, replace_if, text, flags=re.DOTALL)
        
        # Handle {{#unless variable}} ... {{/unless}} blocks  
        unless_pattern = r'\{\{#unless\s+(\w+)\}\}(.*?)\{\{/unless\}\}'
        
        def replace_unless(match):
            var_name = match.group(1)
            content = match.group(2)
            if not context.get(var_name):
                return content
            return ""
        
        text = re.sub(unless_pattern, replace_unless, text, flags=re.DOTALL)
        
        return text
    
    def validate_context(self, context: Dict[str, Any]) -> List[str]:
        """
        Validate that all required variables are provided in context.
        
        Args:
            context: Context dictionary to validate
            
        Returns:
            List of missing variable names
        """
        missing = []
        for var in self.variables:
            if var not in context:
                missing.append(var)
        return missing


class PromptRenderer:
    """Renderer for prompt templates with context injection."""
    
    def __init__(self):
        """Initialize prompt renderer."""
        self.templates: Dict[str, PromptTemplate] = {}
        self.default_context: Dict[str, Any] = {}
    
    def register_template(self, template: PromptTemplate, template_id: str = None):
        """
        Register a template for rendering.
        
        Args:
            template: PromptTemplate to register
            template_id: Unique identifier (uses template.name if not provided)
        """
        template_id = template_id or template.name
        self.templates[template_id] = template
    
    def load_template_from_file(self, file_path: Path, template_id: str = None) -> PromptTemplate:
        """
        Load template from file.
        
        Args:
            file_path: Path to template file
            template_id: Template identifier
            
        Returns:
            Loaded PromptTemplate
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        template_id = template_id or file_path.stem
        template = PromptTemplate(content, name=template_id)
        self.register_template(template, template_id)
        return template
    
    def set_default_context(self, context: Dict[str, Any]):
        """
        Set default context values that will be merged with render context.
        
        Args:
            context: Default context dictionary
        """
        self.default_context.update(context)
    
    def render_template(self, template_id: str, context: Dict[str, Any]) -> str:
        """
        Render a registered template with context.
        
        Args:
            template_id: ID of template to render
            context: Context variables for rendering
            
        Returns:
            Rendered template text
            
        Raises:
            KeyError: If template not found
        """
        if template_id not in self.templates:
            raise KeyError(f"Template '{template_id}' not found")
        
        # Merge default context with provided context
        merged_context = {**self.default_context, **context}
        
        template = self.templates[template_id]
        return template.render(merged_context)
    
    def render_template_with_prompt_context(self, template_id: str, 
                                          prompt_context: PromptContext) -> str:
        """
        Render template using PromptContext object.
        
        Args:
            template_id: ID of template to render
            prompt_context: PromptContext with rendering data
            
        Returns:
            Rendered template text
        """
        # Convert PromptContext to dictionary
        context = self._prompt_context_to_dict(prompt_context)
        return self.render_template(template_id, context)
    
    def _prompt_context_to_dict(self, prompt_context: PromptContext) -> Dict[str, Any]:
        """Convert PromptContext to dictionary for template rendering."""
        return {
            'user_id': prompt_context.user_id,
            'session_id': prompt_context.session_id,
            'message_text': prompt_context.message_text,
            'previous_memories': prompt_context.previous_memories,
            'user_timezone': prompt_context.user_timezone,
            'extraction_mode': prompt_context.extraction_mode.value,
            'memory_types': [mt.value for mt in prompt_context.memory_types],
            'memory_types_list': ', '.join([mt.value for mt in prompt_context.memory_types]),
            'max_memories': prompt_context.max_memories,
            'confidence_threshold': prompt_context.confidence_threshold,
            'timestamp': prompt_context.timestamp.isoformat(),
            'date': prompt_context.timestamp.strftime('%Y-%m-%d'),
            'time': prompt_context.timestamp.strftime('%H:%M:%S'),
            'has_previous_memories': len(prompt_context.previous_memories) > 0,
            'previous_memories_count': len(prompt_context.previous_memories),
            'is_strict_mode': prompt_context.extraction_mode == ExtractionMode.STRICT,
            'is_moderate_mode': prompt_context.extraction_mode == ExtractionMode.MODERATE,
            'is_permissive_mode': prompt_context.extraction_mode == ExtractionMode.PERMISSIVE
        }
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get registered template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[str]:
        """Get list of registered template IDs."""
        return list(self.templates.keys())
    
    def validate_template_context(self, template_id: str, 
                                context: Dict[str, Any]) -> List[str]:
        """
        Validate context for a template.
        
        Args:
            template_id: Template to validate against
            context: Context to validate
            
        Returns:
            List of missing variables
            
        Raises:
            KeyError: If template not found
        """
        if template_id not in self.templates:
            raise KeyError(f"Template '{template_id}' not found")
        
        template = self.templates[template_id]
        merged_context = {**self.default_context, **context}
        return template.validate_context(merged_context)