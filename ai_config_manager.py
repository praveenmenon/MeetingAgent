#!/usr/bin/env python3
"""
AI Configuration Management CLI
"""

import argparse
import json
import sys
from src.meeting_agent.ai_config import get_ai_config, TaskType, ModelParams


def show_current_config(task_type: str = None):
    """Show current AI configuration"""
    config = get_ai_config()
    
    if task_type:
        try:
            task_enum = TaskType(task_type.lower())
            params = config.get_params(task_enum)
            
            print(f"\n=== {task_type.upper()} Configuration ===")
            print(f"Temperature: {params.temperature}")
            print(f"Max Tokens: {params.max_tokens}")
            print(f"Top P: {params.top_p}")
            print(f"Frequency Penalty: {params.frequency_penalty}")
            print(f"Presence Penalty: {params.presence_penalty}")
            print(f"Model Override: {params.model or 'None'}")
            
        except ValueError:
            print(f"Error: Unknown task type '{task_type}'")
            print(f"Available task types: {', '.join([t.value for t in TaskType])}")
            return
    else:
        print("\n=== Current AI Configuration ===")
        summary = config.get_config_summary()
        
        for task_name, params in summary.items():
            print(f"\n{task_name.upper()}:")
            for param, value in params.items():
                print(f"  {param}: {value}")


def update_config(task_type: str, parameter: str, value: str):
    """Update a configuration parameter"""
    config = get_ai_config()
    
    try:
        task_enum = TaskType(task_type.lower())
    except ValueError:
        print(f"Error: Unknown task type '{task_type}'")
        print(f"Available task types: {', '.join([t.value for t in TaskType])}")
        return
    
    # Convert value to appropriate type
    try:
        if parameter in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']:
            value = float(value)
        elif parameter == 'max_tokens':
            value = int(value)
        elif parameter == 'model':
            pass  # Keep as string
        else:
            print(f"Error: Unknown parameter '{parameter}'")
            print("Available parameters: temperature, max_tokens, top_p, frequency_penalty, presence_penalty, model")
            return
    except ValueError:
        print(f"Error: Invalid value '{value}' for parameter '{parameter}'")
        return
    
    # Update configuration
    config.update_task_config(task_enum, **{parameter: value})
    print(f"✅ Updated {task_type}.{parameter} = {value}")


def reset_config(task_type: str = None):
    """Reset configuration to defaults"""
    config = get_ai_config()
    
    if task_type:
        try:
            task_enum = TaskType(task_type.lower())
            config.reset_to_defaults(task_enum)
            print(f"✅ Reset {task_type} configuration to defaults")
        except ValueError:
            print(f"Error: Unknown task type '{task_type}'")
            return
    else:
        config.reset_to_defaults()
        print("✅ Reset all configurations to defaults")


def export_config(filename: str):
    """Export configuration to JSON file"""
    config = get_ai_config()
    summary = config.get_config_summary()
    
    try:
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✅ Configuration exported to {filename}")
    except Exception as e:
        print(f"Error exporting configuration: {e}")


def import_config(filename: str):
    """Import configuration from JSON file"""
    config = get_ai_config()
    
    try:
        with open(filename, 'r') as f:
            imported_config = json.load(f)
        
        for task_name, params in imported_config.items():
            try:
                task_enum = TaskType(task_name.lower())
                
                # Filter out 'model' field if it's 'default'
                update_params = {}
                for param, value in params.items():
                    if param == 'model' and value == 'default':
                        update_params[param] = None
                    else:
                        update_params[param] = value
                
                config.update_task_config(task_enum, **update_params)
                print(f"✅ Imported {task_name} configuration")
                
            except ValueError:
                print(f"⚠️  Skipping unknown task type: {task_name}")
        
        print("✅ Configuration import completed")
        
    except Exception as e:
        print(f"Error importing configuration: {e}")


def benchmark_settings():
    """Show recommended settings for different use cases"""
    print("\n=== Recommended Settings by Use Case ===")
    
    print("\n🎯 ACCURACY-FOCUSED (Financial/Legal/Medical)")
    print("  Temperature: 0.1-0.3 (very low)")
    print("  Top P: 0.6-0.8 (focused)")
    print("  Max Tokens: Depends on output length needed")
    print("  Example: AI_SUMMARIZATION_TEMPERATURE=0.1")
    
    print("\n⚖️  BALANCED (Standard Business Meetings)")
    print("  Temperature: 0.3-0.5 (moderate)")
    print("  Top P: 0.8-0.9 (balanced)")
    print("  Max Tokens: 1000-2000")
    print("  Example: AI_SUMMARIZATION_TEMPERATURE=0.4")
    
    print("\n🎨 CREATIVE (Brainstorming/Innovation)")
    print("  Temperature: 0.6-0.9 (high)")
    print("  Top P: 0.9-1.0 (diverse)")
    print("  Max Tokens: 1500-3000")
    print("  Example: AI_TASK_SUGGESTION_TEMPERATURE=0.8")
    
    print("\n📊 ANALYTICAL (Data Analysis/Research)")
    print("  Temperature: 0.4-0.6 (moderate)")
    print("  Top P: 0.8-0.9 (structured)")
    print("  Frequency Penalty: 0.1-0.2 (reduce repetition)")
    print("  Example: AI_ANALYSIS_TEMPERATURE=0.5")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Manage AI model configurations for Meeting Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all configurations
  python ai_config_manager.py show

  # Show specific task configuration
  python ai_config_manager.py show --task summarization

  # Update a parameter
  python ai_config_manager.py update summarization temperature 0.2

  # Reset to defaults
  python ai_config_manager.py reset --task summarization

  # Export/import configurations
  python ai_config_manager.py export config.json
  python ai_config_manager.py import config.json

  # Show optimization recommendations
  python ai_config_manager.py benchmark

Available Task Types:
  summarization, brief_description, similarity_check, 
  task_suggestion, qa_answering, chunk_combination,
  creative_writing, analysis
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show current configuration')
    show_parser.add_argument('--task', '-t', help='Show specific task configuration')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update configuration parameter')
    update_parser.add_argument('task_type', help='Task type to update')
    update_parser.add_argument('parameter', help='Parameter to update')
    update_parser.add_argument('value', help='New value')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset configuration to defaults')
    reset_parser.add_argument('--task', '-t', help='Reset specific task (default: all)')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export configuration to file')
    export_parser.add_argument('filename', help='Output filename')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import configuration from file')
    import_parser.add_argument('filename', help='Input filename')
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Show optimization recommendations')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'show':
            show_current_config(args.task)
        elif args.command == 'update':
            update_config(args.task_type, args.parameter, args.value)
        elif args.command == 'reset':
            reset_config(args.task)
        elif args.command == 'export':
            export_config(args.filename)
        elif args.command == 'import':
            import_config(args.filename)
        elif args.command == 'benchmark':
            benchmark_settings()
            
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()