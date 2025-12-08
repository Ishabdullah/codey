#!/usr/bin/env python3
"""Codey CLI - Interactive command-line interface"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.engine_v2 import CodeyEngineV2 as CodeyEngine
from cli.colors import (
    success, error, warning, info, bold, dim,
    success_msg, error_msg, warning_msg, info_msg,
    Icons
)

def print_banner():
    """Print Codey banner"""
    banner = """
╔═══════════════════════════════════════════════╗
║                                               ║
║   ██████╗ ██████╗ ██████╗ ███████╗██╗   ██╗  ║
║  ██╔════╝██╔═══██╗██╔══██╗██╔════╝╚██╗ ██╔╝  ║
║  ██║     ██║   ██║██║  ██║█████╗   ╚████╔╝   ║
║  ██║     ██║   ██║██║  ██║██╔══╝    ╚██╔╝    ║
║  ╚██████╗╚██████╔╝██████╔╝███████╗   ██║     ║
║   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝   ╚═╝     ║
║                                               ║
║  Local AI Coding Assistant                   ║
║  Powered by llama.cpp                         ║
║                                               ║
╚═══════════════════════════════════════════════╝
"""
    print(banner)

def print_help():
    """Print help information with colors and categories"""
    print(f"\n{bold('═' * 60)}")
    print(f"{bold(info('  CODEY COMMAND REFERENCE'))}")
    print(f"{bold('═' * 60)}\n")

    # File Operations
    print(f"{bold(success(f'{Icons.FILE} FILE OPERATIONS'))}")
    print(f"  {info('create')} <filename> <description>  - Create a new file")
    print(f"  {info('edit')} <filename> <changes>        - Edit an existing file")
    print(f"  {info('read')} <filename>                  - Display file contents")
    print(f"  {info('delete')} <filename>                - Delete a file")
    print(f"  {info('list')} files                       - List all files in workspace")
    print()

    # Git Operations
    print(f"{bold(success(f'{Icons.GIT} GIT OPERATIONS'))}")
    print(f"  {info('clone')} <url> [destination]        - Clone a repository")
    print(f"  {info('git status')}                       - Check git status")
    print(f"  {info('commit')} with message \"msg\"       - Commit changes")
    print(f"  {info('push')} [remote] [branch]           - Push to remote")
    print(f"  {info('pull')} [remote] [branch]           - Pull from remote")
    print(f"  {info('git init')}                         - Initialize git repository")
    print()

    # Shell Operations
    print(f"{bold(success(f'{Icons.SHELL} SHELL OPERATIONS'))}")
    print(f"  {info('mkdir')} <directory>                - Create directory")
    print(f"  {info('install')} <package>                - Install Python package")
    print(f"  {info('install')} requirements.txt         - Install from requirements.txt")
    print(f"  {info('run')} <filename>                   - Run Python file")
    print(f"  {info('execute')} <command>                - Run shell command")
    print()

    # Advanced Features
    print(f"{bold(success(f'{Icons.ROBOT} ADVANCED FEATURES'))}")
    print(f"  {info('plan')} <task>                      - Create autonomous task plan")
    print(f"  {info('execute plan')}                     - Run current plan")
    print(f"  {info('show plan')}                        - Display current plan")
    print(f"  {info('debug')} <file>                     - Analyze file for issues")
    print(f"  {info('ask')} <question>                   - Query Perplexity API")
    print(f"  {info('info')}                             - Show system information")
    print()

    # Natural Language
    print(f"{bold(success(f'{Icons.WRENCH} NATURAL LANGUAGE'))}")
    print(f"  {dim('Keep commands simple and direct!')}")
    print(f"  {dim('Examples:')}")
    print(f"    • {info('create hello.py that prints hello world')}")
    print(f"    • {info('clone https://github.com/user/repo ~/MyProject')}")
    print(f"    • {info('install numpy')}")
    print()

    # System Commands
    print(f"{bold(success('SYSTEM COMMANDS'))}")
    print(f"  {info('help, ?')}          - Show this help")
    print(f"  {info('clear')}             - Clear screen")
    print(f"  {info('exit, quit')}        - Exit Codey")
    print()

    # Tips
    print(f"{bold(warning(f'{Icons.INFO} TIPS'))}")
    print(f"  • Use ONE command at a time for best results")
    print(f"  • Supports ~/ for home directory paths")
    print(f"  • Git/shell operations work anywhere on your device")
    print(f"  • All operations require permission approval")
    print()
    print(f"{bold('═' * 60)}\n")

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def interactive_mode():
    """Run Codey in interactive mode"""
    print_banner()
    print(f"\n{info_msg('Initializing Codey...')}\n")

    try:
        engine = CodeyEngine()
        print(f"{success_msg('Ready!')} Type {info('help')} for commands or start coding.\n")
    except FileNotFoundError as e:
        print(f"\n{error_msg('Model not found')}")
        print(f"\n{warning('Please ensure you have a GGUF model in ~/codey/LLM_Models/')}")
        print(f"{warning('Or update config.json with the correct model path.')}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{error_msg(f'Failed to initialize Codey: {e}')}")
        sys.exit(1)

    # Main interaction loop
    while True:
        try:
            user_input = input("\ncodey> ").strip()

            if not user_input:
                continue

            # Handle system commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print(f"\n{info_msg('Shutting down Codey...')}")
                engine.shutdown()
                print(f"{success_msg('Goodbye!')}\n")
                break

            elif user_input.lower() in ['help', '?', 'h']:
                print_help()
                continue

            elif user_input.lower() in ['clear', 'cls']:
                clear_screen()
                print_banner()
                continue

            # Process command through engine
            response = engine.process_command(user_input)
            print(f"\n{response}")

        except KeyboardInterrupt:
            print(f"\n\n{warning_msg('Interrupted')} Type {info('exit')} to quit or continue working.")
            continue

        except EOFError:
            print(f"\n{info_msg('Shutting down Codey...')}")
            engine.shutdown()
            break

        except Exception as e:
            print(f"\n{error_msg(f'Error: {e}')}")
            continue

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Command-line argument mode
        if sys.argv[1] in ['-h', '--help']:
            print_help()
        elif sys.argv[1] in ['-v', '--version']:
            print("Codey v1.0.0 - Local AI Coding Assistant")
        else:
            print("Unknown option. Use --help for usage information.")
    else:
        # Interactive mode
        interactive_mode()

if __name__ == "__main__":
    main()
