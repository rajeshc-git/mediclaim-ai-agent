import sys
import os
import json
from agent.core import AgentOrchestrator

# ANSI escape codes for gorgeous colors
CLR_HEADER = "\033[95m"
CLR_USER = "\033[94m"
CLR_THOUGHT = "\033[93m"
CLR_TOOL = "\033[96m"
CLR_OBS = "\033[90m"
CLR_ANSWER = "\033[92m"
CLR_ERROR = "\033[91m"
CLR_BOLD = "\033[1m"
CLR_RESET = "\033[0m"

def print_banner():
    banner = f"""
{CLR_HEADER}{CLR_BOLD}=============================================================
             🤖 Autonomous ReAct AI Agent CLI 🤖
============================================================={CLR_RESET}
Welcome! This agent reasoning loop supports files and web searches.
Type your commands below. To exit, type 'exit' or 'quit'.
-------------------------------------------------------------
"""
    print(banner)

def main():
    # Reconfigure stdout/stderr to UTF-8 on Windows to safely print emojis
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # Make sure terminal supports colors (specifically on Windows CMD/Powershell)
    if sys.platform == "win32":
        os.system("color")
        
    print_banner()
    
    # Clear claims_audit directory on startup in CLI mode to avoid model hallucinating with leftover analysis reports
    audit_dir = "claims_audit"
    if os.path.exists(audit_dir) and os.path.isdir(audit_dir):
        try:
            for f in os.listdir(audit_dir):
                f_path = os.path.join(audit_dir, f)
                if os.path.isfile(f_path):
                    os.remove(f_path)
        except Exception:
            pass
            
    # Initialize the core agent
    try:
        orchestrator = AgentOrchestrator()
    except Exception as e:
        print(f"{CLR_ERROR}Fatal Error: Failed to initialize orchestrator: {str(e)}{CLR_RESET}")
        sys.exit(1)

    while True:
        try:
            user_input = input(f"\n{CLR_USER}{CLR_BOLD}User ➔{CLR_RESET} ")
            if user_input.strip().lower() in ("exit", "quit"):
                print(f"\n{CLR_HEADER}Goodbye! Closing agent session.{CLR_RESET}")
                break
                
            if not user_input.strip():
                continue

            # Run agent loop generator and print steps live
            runner = orchestrator.run(user_input)
            
            while True:
                try:
                    event = next(runner)
                    event_type = event["type"]
                    
                    if event_type == "step_start":
                        print(f"\n{CLR_HEADER}─── Reasoning Turn #{event['step']} ───{CLR_RESET}")
                        
                    elif event_type == "thought":
                        print(f"{CLR_THOUGHT}{CLR_BOLD}Thought:{CLR_RESET} {CLR_THOUGHT}{event['text']}{CLR_RESET}")
                        
                    elif event_type == "tool_call":
                        print(f"{CLR_TOOL}{CLR_BOLD}Action ➔{CLR_RESET} {CLR_TOOL}Invoking '{event['tool']}' with args: {json.dumps(event['args'])}{CLR_RESET}")
                        
                    elif event_type == "tool_observation":
                        print(f"{CLR_OBS}{CLR_BOLD}Observation ➔{CLR_RESET}\n{CLR_OBS}{event['observation']}{CLR_RESET}")
                        
                    elif event_type == "tool_error":
                        print(f"{CLR_ERROR}{CLR_BOLD}Tool Error ➔{CLR_RESET} {CLR_ERROR}{event['error']}{CLR_RESET}")
                        
                    elif event_type == "final_answer":
                        print(f"\n{CLR_ANSWER}{CLR_BOLD}Response:{CLR_RESET}\n{CLR_ANSWER}{event['text']}{CLR_RESET}")
                        
                except StopIteration as stop:
                    # Final answer is returned when generator raises StopIteration
                    break
                    
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{CLR_HEADER}Session interrupted. Goodbye!{CLR_RESET}")
            break
        except Exception as e:
            print(f"\n{CLR_ERROR}An unexpected error occurred during execution: {str(e)}{CLR_RESET}")

if __name__ == "__main__":
    main()
