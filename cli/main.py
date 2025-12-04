#!/usr/bin/env python3
"""Codey CLI - Interactive command-line interface"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.engine_v2 import CodeyEngineV2 as CodeyEngine

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
    """Print help information"""
    help_text = """
Available Commands:

  File Operations:
    create <filename> <description>  - Create a new file
    edit <filename> <changes>        - Edit an existing file
    read <filename>                  - Display file contents
    delete <filename>                - Delete a file
    list files                       - List all files in workspace

  Natural Language:
    Just describe what you want!
    Examples:
      - "create hello.py that prints hello world"
      - "write a function to calculate fibonacci"
      - "add error handling to server.py"
      - "explain what config.py does"

  System:
    help, ?          - Show this help
    clear            - Clear screen
    exit, quit       - Exit Codey

  Tips:
    - Files are saved in ~/codey/workspace/
    - Backups are created before edits
    - Use natural language - Codey understands context!
"""
    print(help_text)

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def interactive_mode():
    """Run Codey in interactive mode"""
    print_banner()
    print("\nInitializing Codey...")

    try:
        engine = CodeyEngine()
        print("Ready! Type 'help' for commands or start coding.\n")
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease ensure you have a GGUF model in ~/codey/LLM_Models/")
        print("Or update config.json with the correct model path.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFailed to initialize Codey: {e}")
        sys.exit(1)

    # Main interaction loop
    while True:
        try:
            user_input = input("\ncodey> ").strip()

            if not user_input:
                continue

            # Handle system commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nShutting down Codey...")
                engine.shutdown()
                print("Goodbye!")
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
            print("\n\nInterrupted. Type 'exit' to quit or continue working.")
            continue

        except EOFError:
            print("\nShutting down Codey...")
            engine.shutdown()
            break

        except Exception as e:
            print(f"\nError: {e}")
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
