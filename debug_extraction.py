#!/usr/bin/env python3
"""
Debug script to see raw LLM responses for memory extraction.
"""
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / 'src'))

from llm.ollama_client import OllamaClient
from prompts.memory_extraction import MemoryExtractionPrompts
from prompts.types import PromptContext, ExtractionMode
from processing.preprocessor import MessagePreprocessor

def debug_extraction(message: str):
    """Debug memory extraction for a message."""
    print(f"\n{'='*60}")
    print(f"DEBUGGING MESSAGE: '{message}'")
    print(f"{'='*60}\n")
    
    # Step 1: Preprocess
    preprocessor = MessagePreprocessor()
    preprocessed = preprocessor.preprocess(message)
    
    print("PREPROCESSING RESULTS:")
    print(f"  - Word count: {preprocessed.word_count}")
    print(f"  - Complexity: {preprocessed.complexity_score:.3f}")
    print(f"  - Should extract: {preprocessor.should_extract_memories(preprocessed)}")
    
    if not preprocessor.should_extract_memories(preprocessed):
        print("\n❌ Message skipped by preprocessor!")
        return
    
    hints = preprocessor.get_extraction_hints(preprocessed)
    print(f"  - Suggested mode: {hints['extraction_mode']}")
    print(f"  - Suggested types: {hints['suggested_memory_types']}")
    
    # Step 2: Build prompt
    prompts = MemoryExtractionPrompts()
    context = PromptContext(
        user_id="test_user",
        session_id="test_session",
        message_text=preprocessed.cleaned_text,
        extraction_mode=ExtractionMode(hints['extraction_mode'])
    )
    
    full_prompt = prompts.get_full_extraction_prompt(context)
    
    print(f"\nPROMPT PREVIEW (first 500 chars):")
    print("-" * 40)
    print(full_prompt[:500] + "...")
    
    # Step 3: Call LLM
    print(f"\nCALLING LLM...")
    client = OllamaClient()
    
    try:
        response = client.generate(full_prompt, options={'temperature': 0.3})
        
        print(f"\nRAW LLM RESPONSE:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        # Try to parse
        print(f"\nPARSING ATTEMPT:")
        try:
            parsed = json.loads(response.strip())
            print("✓ Valid JSON")
            print(f"  - Memories found: {len(parsed.get('memories', []))}")
            for mem in parsed.get('memories', []):
                print(f"    • {mem.get('content', 'NO CONTENT')}")
        except json.JSONDecodeError as e:
            print(f"✗ JSON Parse Error: {e}")
            
    except Exception as e:
        print(f"✗ LLM Error: {e}")

def main():
    """Test various messages."""
    test_messages = [
        "Hi, my name is Jason",
        "My name is Jason",
        "I am Jason",
        "Jason is my name and I work as a developer",
        "My name is John Smith, I work at Google, and I have a cat"
    ]
    
    for msg in test_messages:
        debug_extraction(msg)
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()