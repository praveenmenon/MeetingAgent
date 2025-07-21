#!/usr/bin/env python3
"""
Rate limit monitoring and management utility
"""

import argparse
import json
import time
import sys
from datetime import datetime, timedelta
from src.meeting_agent.ai_client import AIClient
from src.meeting_agent.rate_limiter import get_rate_limiter, APIProvider, RetryConfig, configure_rate_limiter


def format_timestamp(timestamp: float) -> str:
    """Format timestamp for display"""
    if timestamp == 0:
        return "No backoff"
    
    if timestamp < time.time():
        return "Ready"
    
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def display_rate_limit_status():
    """Display current rate limit status"""
    client = AIClient()
    status = client.get_rate_limit_status()
    
    print("\n=== AI API Rate Limit Status ===\n")
    
    for provider_name, provider_status in status.items():
        print(f"🔹 {provider_name.upper()}")
        print(f"  Recent requests (last minute): {provider_status['requests_last_minute']}")
        
        if provider_status['limit_requests']:
            remaining_pct = (provider_status['remaining_requests'] / provider_status['limit_requests']) * 100
            print(f"  Request limit: {provider_status['remaining_requests']}/{provider_status['limit_requests']} ({remaining_pct:.1f}% remaining)")
        else:
            print(f"  Request limit: Unknown")
        
        if provider_status['limit_tokens']:
            remaining_pct = (provider_status['remaining_tokens'] / provider_status['limit_tokens']) * 100
            print(f"  Token limit: {provider_status['remaining_tokens']}/{provider_status['limit_tokens']} ({remaining_pct:.1f}% remaining)")
        else:
            print(f"  Token limit: Unknown")
        
        print(f"  Queue size: {provider_status['queue_size']}")
        print(f"  Backoff status: {format_timestamp(provider_status['backoff_until'])}")
        
        if provider_status['reset_requests']:
            reset_dt = datetime.fromtimestamp(provider_status['reset_requests'])
            print(f"  Request reset: {reset_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print()


def process_queued_requests(max_requests: int):
    """Process queued requests"""
    client = AIClient()
    
    print(f"Processing up to {max_requests} queued requests...")
    results = client.process_queued_requests(max_requests)
    
    total_processed = results['openai_processed'] + results['anthropic_processed']
    
    if total_processed > 0:
        print(f"✅ Processed {total_processed} requests:")
        if results['openai_processed']:
            print(f"  OpenAI: {results['openai_processed']} requests")
        if results['anthropic_processed']:
            print(f"  Anthropic: {results['anthropic_processed']} requests")
    else:
        print("ℹ️  No requests were processed (queue empty or rate limits active)")


def configure_retry_settings(args):
    """Configure retry settings"""
    config = RetryConfig()
    
    if args.max_retries is not None:
        config.max_retries = args.max_retries
    if args.base_delay is not None:
        config.base_delay = args.base_delay
    if args.max_delay is not None:
        config.max_delay = args.max_delay
    if args.rate_limit_delay is not None:
        config.rate_limit_delay = args.rate_limit_delay
    if args.quota_delay is not None:
        config.quota_exceeded_delay = args.quota_delay
    if args.jitter is not None:
        config.jitter = args.jitter
    
    configure_rate_limiter(config)
    print("✅ Rate limiter configuration updated")
    
    print("\nCurrent configuration:")
    print(f"  Max retries: {config.max_retries}")
    print(f"  Base delay: {config.base_delay}s")
    print(f"  Max delay: {config.max_delay}s")
    print(f"  Rate limit delay: {config.rate_limit_delay}s")
    print(f"  Quota exceeded delay: {config.quota_exceeded_delay}s")
    print(f"  Jitter enabled: {config.jitter}")


def watch_rate_limits(interval: int):
    """Watch rate limits continuously"""
    print(f"👁️  Watching rate limits (refresh every {interval}s). Press Ctrl+C to stop.\n")
    
    try:
        while True:
            # Clear screen (simple version)
            print("\033[2J\033[H", end="")
            
            print(f"🕒 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            display_rate_limit_status()
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")


def clear_backoff(provider: str = None):
    """Clear backoff periods"""
    rate_limiter = get_rate_limiter()
    
    if provider:
        try:
            provider_enum = APIProvider(provider.lower())
            rate_limiter.backoff_until[provider_enum] = 0
            print(f"✅ Cleared backoff for {provider}")
        except ValueError:
            print(f"❌ Unknown provider: {provider}")
            print("Available providers: openai, anthropic")
    else:
        # Clear all backoffs
        for provider_enum in APIProvider:
            rate_limiter.backoff_until[provider_enum] = 0
        print("✅ Cleared all backoff periods")


def clear_queues(provider: str = None):
    """Clear request queues"""
    rate_limiter = get_rate_limiter()
    
    if provider:
        try:
            provider_enum = APIProvider(provider.lower())
            rate_limiter.request_queues[provider_enum].clear()
            print(f"✅ Cleared queue for {provider}")
        except ValueError:
            print(f"❌ Unknown provider: {provider}")
            print("Available providers: openai, anthropic")
    else:
        # Clear all queues
        for provider_enum in APIProvider:
            rate_limiter.request_queues[provider_enum].clear()
        print("✅ Cleared all request queues")


def export_status(filename: str):
    """Export rate limit status to file"""
    client = AIClient()
    status = client.get_rate_limit_status()
    
    # Add timestamp
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "rate_limits": status
    }
    
    try:
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        print(f"✅ Rate limit status exported to {filename}")
    except Exception as e:
        print(f"❌ Failed to export status: {e}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Monitor and manage API rate limits for Meeting Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current status
  python rate_limit_monitor.py status

  # Process queued requests
  python rate_limit_monitor.py process --max-requests 20

  # Watch rate limits in real-time
  python rate_limit_monitor.py watch --interval 10

  # Configure retry settings
  python rate_limit_monitor.py configure --max-retries 3 --base-delay 2

  # Clear backoff periods
  python rate_limit_monitor.py clear-backoff --provider openai

  # Clear request queues
  python rate_limit_monitor.py clear-queues

  # Export status to file
  python rate_limit_monitor.py export status.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current rate limit status')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process queued requests')
    process_parser.add_argument('--max-requests', '-n', type=int, default=10, 
                               help='Maximum number of requests to process')
    
    # Watch command
    watch_parser = subparsers.add_parser('watch', help='Watch rate limits continuously')
    watch_parser.add_argument('--interval', '-i', type=int, default=5,
                             help='Refresh interval in seconds')
    
    # Configure command
    config_parser = subparsers.add_parser('configure', help='Configure retry settings')
    config_parser.add_argument('--max-retries', type=int, help='Maximum number of retries')
    config_parser.add_argument('--base-delay', type=float, help='Base delay in seconds')
    config_parser.add_argument('--max-delay', type=float, help='Maximum delay in seconds')
    config_parser.add_argument('--rate-limit-delay', type=float, help='Rate limit delay in seconds')
    config_parser.add_argument('--quota-delay', type=float, help='Quota exceeded delay in seconds')
    config_parser.add_argument('--jitter', type=bool, help='Enable jitter')
    
    # Clear backoff command
    backoff_parser = subparsers.add_parser('clear-backoff', help='Clear backoff periods')
    backoff_parser.add_argument('--provider', '-p', choices=['openai', 'anthropic'], 
                               help='Clear backoff for specific provider (default: all)')
    
    # Clear queues command
    queue_parser = subparsers.add_parser('clear-queues', help='Clear request queues')
    queue_parser.add_argument('--provider', '-p', choices=['openai', 'anthropic'],
                             help='Clear queue for specific provider (default: all)')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export rate limit status')
    export_parser.add_argument('filename', help='Output filename')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'status':
            display_rate_limit_status()
        elif args.command == 'process':
            process_queued_requests(args.max_requests)
        elif args.command == 'watch':
            watch_rate_limits(args.interval)
        elif args.command == 'configure':
            configure_retry_settings(args)
        elif args.command == 'clear-backoff':
            clear_backoff(args.provider)
        elif args.command == 'clear-queues':
            clear_queues(args.provider)
        elif args.command == 'export':
            export_status(args.filename)
            
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()