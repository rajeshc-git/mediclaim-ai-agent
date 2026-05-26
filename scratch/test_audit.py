import os
import sys
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.core import AgentOrchestrator

def main():
    print("Initializing AgentOrchestrator...")
    orchestrator = AgentOrchestrator()
    query = "Audit the bill for Saravana"
    print(f"Deploying agent with short query: '{query}'")
    
    runner = orchestrator.run(query)
    for event in runner:
        event_type = event["type"]
        if event_type == "step_start":
            print(f"\n[Turn #{event['step']}]")
        elif event_type == "thought":
            print(f"Thought: {event['text']}")
        elif event_type == "tool_call":
            print(f"Action: {event['tool']} with args: {event['args']}")
        elif event_type == "tool_observation":
            print(f"Observation: {event['observation'][:150]}...")
        elif event_type == "tool_error":
            print(f"Tool Error: {event['error']}")
        elif event_type == "final_answer":
            print(f"\n================ FINAL ANSWER ================\n{event['text']}\n==============================================")

if __name__ == "__main__":
    main()
