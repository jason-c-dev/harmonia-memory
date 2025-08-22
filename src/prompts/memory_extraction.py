"""
Memory extraction prompts for different types of memories.
"""
import json
from typing import Dict, List, Any
from pathlib import Path

from .template_engine import PromptTemplate, PromptRenderer
from .types import MemoryType, PromptContext, ExtractionMode


class MemoryExtractionPrompts:
    """Collection of memory extraction prompts for different memory types."""
    
    def __init__(self):
        """Initialize memory extraction prompts."""
        self.renderer = PromptRenderer()
        self._load_base_templates()
        self._setup_default_context()
    
    def _setup_default_context(self):
        """Setup default context values for all templates."""
        default_context = {
            'system_name': 'Harmonia Memory System',
            'current_date': 'current system date',
            'output_format': 'JSON'
        }
        self.renderer.set_default_context(default_context)
    
    def _load_base_templates(self):
        """Load base prompt templates for memory extraction."""
        
        # Base system prompt
        base_system_prompt = """You are a memory extraction AI for the Harmonia Memory System. Your task is to analyze user messages and extract meaningful memories that should be preserved.

EXTRACTION GUIDELINES:
- EXTRACT ALL DISTINCT FACTS: Each separate piece of information should be a separate memory
- Extract memories that are personal, factual, emotional, or otherwise significant
- Focus on information that would be valuable to remember in future conversations
- Maintain accuracy - only extract what is explicitly stated or clearly implied
- Assign appropriate confidence scores (0.0-1.0) based on clarity and certainty
- Categorize memories by type: {{memory_types_list}}

CRITICAL RULE: If a message contains multiple facts, create multiple memories.

EXAMPLES:
Input: "My name is John Smith, I work at Google, I have a cat"
MUST extract 3 memories:
1. "User's name is John Smith" (personal)
2. "User works at Google" (factual)  
3. "User has a cat" (relational)

EXTRACTION MODE: {{extraction_mode}}
{{#if is_strict_mode}}
- Only extract explicit, clearly stated information
- Require high confidence (>0.8) for all extractions
{{/if}}
{{#if is_moderate_mode}}
- Extract clear statements and reasonable inferences
- Balance accuracy with completeness
{{/if}}
{{#if is_permissive_mode}}
- Extract all potentially valuable information
- Include weak inferences and implications
{{/if}}

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
  "memories": [
    {
      "content": "Clear, concise description of the memory",
      "memory_type": "one of: personal, factual, emotional, procedural, episodic, relational, preference, goal, skill, temporal",
      "confidence": 0.95,
      "entities": ["person", "place", "thing"],
      "temporal_info": "time/date information if relevant",
      "context": "situational context if helpful",
      "relationships": ["connection to other concepts"]
    }
  ],
  "extraction_confidence": 0.92,
  "reasoning": "Brief explanation of extraction decisions"
}

IMPORTANT: Return ONLY valid JSON. No additional text before or after."""

        # Main extraction prompt
        main_extraction_prompt = """{{#if has_previous_memories}}
PREVIOUS MEMORIES FOR CONTEXT:
{{previous_memories}}

{{/if}}
USER MESSAGE TO ANALYZE:
"{{message_text}}"

EXTRACTION PARAMETERS:
- Maximum memories to extract: {{max_memories}}
- Minimum confidence threshold: {{confidence_threshold}}
- User timezone: {{user_timezone}}
- Session ID: {{session_id}}

Analyze the user message and extract relevant memories according to the guidelines. Focus on information that would be valuable for future conversations with this user."""

        # Type-specific extraction prompts
        personal_memory_prompt = """Focus on extracting PERSONAL memories from this message:
- Personal information about the user
- Biographical details
- Personal characteristics or traits
- Individual circumstances or situations

USER MESSAGE: "{{message_text}}"

Extract personal memories following the standard JSON format."""

        factual_memory_prompt = """Focus on extracting FACTUAL memories from this message:
- Objective facts and information
- Data points and statistics
- Verifiable information
- Knowledge claims

USER MESSAGE: "{{message_text}}"

Extract factual memories following the standard JSON format."""

        emotional_memory_prompt = """Focus on extracting EMOTIONAL memories from this message:
- Expressed feelings and emotions
- Emotional reactions and responses
- Mood indicators
- Emotional states and changes

USER MESSAGE: "{{message_text}}"

Extract emotional memories following the standard JSON format."""

        procedural_memory_prompt = """Focus on extracting PROCEDURAL memories from this message:
- How-to information and processes
- Step-by-step procedures
- Methods and techniques
- Workflow descriptions

USER MESSAGE: "{{message_text}}"

Extract procedural memories following the standard JSON format."""

        episodic_memory_prompt = """Focus on extracting EPISODIC memories from this message:
- Specific events and experiences
- Temporal occurrences
- Narrative episodes
- Situational memories

USER MESSAGE: "{{message_text}}"

Extract episodic memories following the standard JSON format."""

        relational_memory_prompt = """Focus on extracting RELATIONAL memories from this message:
- Relationships between people
- Connections between concepts
- Social interactions
- Network associations

USER MESSAGE: "{{message_text}}"

Extract relational memories following the standard JSON format."""

        preference_memory_prompt = """Focus on extracting PREFERENCE memories from this message:
- Likes and dislikes
- Preferences and opinions
- Taste and style choices
- Value judgments

USER MESSAGE: "{{message_text}}"

Extract preference memories following the standard JSON format."""

        goal_memory_prompt = """Focus on extracting GOAL memories from this message:
- Objectives and targets
- Aspirations and ambitions
- Plans and intentions
- Desired outcomes

USER MESSAGE: "{{message_text}}"

Extract goal memories following the standard JSON format."""

        skill_memory_prompt = """Focus on extracting SKILL memories from this message:
- Abilities and competencies
- Learned skills and expertise
- Talents and capabilities
- Proficiencies

USER MESSAGE: "{{message_text}}"

Extract skill memories following the standard JSON format."""

        temporal_memory_prompt = """Focus on extracting TEMPORAL memories from this message:
- Time-related information
- Schedules and appointments
- Dates and deadlines
- Temporal patterns

USER MESSAGE: "{{message_text}}"

Extract temporal memories following the standard JSON format."""

        # Register all templates
        templates = {
            'base_system': PromptTemplate(base_system_prompt, 'base_system', '1.0'),
            'main_extraction': PromptTemplate(main_extraction_prompt, 'main_extraction', '1.0'),
            'personal_memory': PromptTemplate(personal_memory_prompt, 'personal_memory', '1.0'),
            'factual_memory': PromptTemplate(factual_memory_prompt, 'factual_memory', '1.0'),
            'emotional_memory': PromptTemplate(emotional_memory_prompt, 'emotional_memory', '1.0'),
            'procedural_memory': PromptTemplate(procedural_memory_prompt, 'procedural_memory', '1.0'),
            'episodic_memory': PromptTemplate(episodic_memory_prompt, 'episodic_memory', '1.0'),
            'relational_memory': PromptTemplate(relational_memory_prompt, 'relational_memory', '1.0'),
            'preference_memory': PromptTemplate(preference_memory_prompt, 'preference_memory', '1.0'),
            'goal_memory': PromptTemplate(goal_memory_prompt, 'goal_memory', '1.0'),
            'skill_memory': PromptTemplate(skill_memory_prompt, 'skill_memory', '1.0'),
            'temporal_memory': PromptTemplate(temporal_memory_prompt, 'temporal_memory', '1.0')
        }
        
        for template_id, template in templates.items():
            self.renderer.register_template(template, template_id)
    
    def get_system_prompt(self, prompt_context: PromptContext) -> str:
        """
        Get the system prompt for memory extraction.
        
        Args:
            prompt_context: Context for prompt rendering
            
        Returns:
            Rendered system prompt
        """
        return self.renderer.render_template_with_prompt_context('base_system', prompt_context)
    
    def get_main_extraction_prompt(self, prompt_context: PromptContext) -> str:
        """
        Get the main extraction prompt.
        
        Args:
            prompt_context: Context for prompt rendering
            
        Returns:
            Rendered extraction prompt
        """
        return self.renderer.render_template_with_prompt_context('main_extraction', prompt_context)
    
    def get_full_extraction_prompt(self, prompt_context: PromptContext) -> str:
        """
        Get complete prompt combining system and extraction prompts.
        
        Args:
            prompt_context: Context for prompt rendering
            
        Returns:
            Complete rendered prompt
        """
        system_prompt = self.get_system_prompt(prompt_context)
        extraction_prompt = self.get_main_extraction_prompt(prompt_context)
        
        return f"{system_prompt}\n\n{extraction_prompt}"
    
    def get_type_specific_prompt(self, memory_type: MemoryType, 
                               prompt_context: PromptContext) -> str:
        """
        Get prompt for extracting specific memory type.
        
        Args:
            memory_type: Type of memory to extract
            prompt_context: Context for prompt rendering
            
        Returns:
            Type-specific extraction prompt
        """
        template_map = {
            MemoryType.PERSONAL: 'personal_memory',
            MemoryType.FACTUAL: 'factual_memory',
            MemoryType.EMOTIONAL: 'emotional_memory',
            MemoryType.PROCEDURAL: 'procedural_memory',
            MemoryType.EPISODIC: 'episodic_memory',
            MemoryType.RELATIONAL: 'relational_memory',
            MemoryType.PREFERENCE: 'preference_memory',
            MemoryType.GOAL: 'goal_memory',
            MemoryType.SKILL: 'skill_memory',
            MemoryType.TEMPORAL: 'temporal_memory'
        }
        
        template_id = template_map.get(memory_type)
        if not template_id:
            raise ValueError(f"No template available for memory type: {memory_type}")
        
        system_prompt = self.get_system_prompt(prompt_context)
        type_prompt = self.renderer.render_template_with_prompt_context(template_id, prompt_context)
        
        return f"{system_prompt}\n\n{type_prompt}"
    
    def get_multi_type_prompt(self, memory_types: List[MemoryType], 
                            prompt_context: PromptContext) -> str:
        """
        Get prompt for extracting multiple specific memory types.
        
        Args:
            memory_types: List of memory types to extract
            prompt_context: Context for prompt rendering
            
        Returns:
            Multi-type extraction prompt
        """
        # Update context to focus on specific types
        focused_context = PromptContext(
            user_id=prompt_context.user_id,
            session_id=prompt_context.session_id,
            message_text=prompt_context.message_text,
            previous_memories=prompt_context.previous_memories,
            user_timezone=prompt_context.user_timezone,
            extraction_mode=prompt_context.extraction_mode,
            memory_types=memory_types,  # Override with specific types
            max_memories=prompt_context.max_memories,
            confidence_threshold=prompt_context.confidence_threshold,
            timestamp=prompt_context.timestamp
        )
        
        return self.get_full_extraction_prompt(focused_context)
    
    def create_few_shot_prompt(self, prompt_context: PromptContext, 
                             examples: List[Dict[str, Any]]) -> str:
        """
        Create a few-shot learning prompt with examples.
        
        Args:
            prompt_context: Context for prompt rendering
            examples: List of example message/memory pairs
            
        Returns:
            Few-shot prompt with examples
        """
        system_prompt = self.get_system_prompt(prompt_context)
        
        examples_text = ""
        for i, example in enumerate(examples, 1):
            examples_text += f"\nEXAMPLE {i}:\n"
            examples_text += f"Message: \"{example['message']}\"\n"
            examples_text += f"Extracted Memories: {json.dumps(example['memories'], indent=2)}\n"
        
        main_prompt = self.get_main_extraction_prompt(prompt_context)
        
        return f"{system_prompt}\n\nHere are some examples of proper memory extraction:\n{examples_text}\n\nNow extract memories from this message:\n{main_prompt}"
    
    def validate_extraction_response(self, response: str) -> Dict[str, Any]:
        """
        Validate and parse LLM response for memory extraction.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed and validated response dictionary
            
        Raises:
            ValueError: If response is invalid
        """
        try:
            # Try to parse as JSON
            data = json.loads(response.strip())
            
            # Validate required fields
            if 'memories' not in data:
                raise ValueError("Response missing 'memories' field")
            
            if not isinstance(data['memories'], list):
                raise ValueError("'memories' field must be a list")
            
            # Validate each memory
            for i, memory in enumerate(data['memories']):
                required_fields = ['content', 'memory_type', 'confidence']
                for field in required_fields:
                    if field not in memory:
                        raise ValueError(f"Memory {i} missing required field '{field}'")
                
                # Validate memory type
                if memory['memory_type'] not in [mt.value for mt in MemoryType]:
                    raise ValueError(f"Invalid memory type: {memory['memory_type']}")
                
                # Validate confidence
                if not 0.0 <= memory['confidence'] <= 1.0:
                    raise ValueError(f"Invalid confidence score: {memory['confidence']}")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
    
    def get_available_templates(self) -> List[str]:
        """Get list of available prompt templates."""
        return self.renderer.list_templates()
    
    def get_template_info(self, template_id: str) -> Dict[str, Any]:
        """
        Get information about a specific template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template information dictionary
        """
        template = self.renderer.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        
        return {
            'name': template.name,
            'version': template.version,
            'variables': template.variables,
            'template_text': template.template_text[:200] + "..." if len(template.template_text) > 200 else template.template_text
        }