"""
Deployer Tools – Production deployment with rollback capability.
"""
import json
import time
from datetime import datetime
from crewai.tools import tool
from loguru import logger

@tool("Request Human Approval")
def request_approval_tool(action_description: str) -> str:
    """
    Pause execution and request explicit human approval before proceeding.
    Returns 'approved' if user types 'yes', otherwise 'denied'.
    """
    print("\n" + "="*60)
    print("⏸️  HUMAN APPROVAL REQUIRED")
    print("="*60)
    print(f"Action: {action_description}")
    print("-"*60)
    
    while True:
        response = input("Approve? (yes/no): ").strip().lower()
        if response in ["yes", "y"]:
            print("✅ Approved. Proceeding...\n")
            return "approved"
        elif response in ["no", "n"]:
            print("❌ Denied. Aborting...\n")
            return "denied"
        else:
            print("Please type 'yes' or 'no'")

@tool("Deploy to Production")
def deploy_to_production_tool(client_id: str, deployment_package: str) -> str:
    """
    Simulate deploying a verified fix to production.
    """
    logger.info(f"Deploying fix to production for client {client_id}")
    
    result = {
        "client_id": client_id,
        "deployment_id": f"deploy_{client_id}_{int(time.time())}",
        "timestamp": datetime.now().isoformat(),
        "status": "deployed",
        "production_url": f"https://{client_id}.example.com",
        "steps": [
            "Verified QA approval",
            "Switched traffic to new version",
            "Confirmed health check passed"
        ],
        "message": "Deployment successful. Fix is now live."
    }
    
    # Simulate deployment delay
    time.sleep(1)
    
    return json.dumps(result, indent=2)

@tool("Emergency Rollback")
def emergency_rollback_tool(client_id: str, reason: str) -> str:
    """
    Rollback production to previous version in case of failure.
    """
    logger.warning(f"EMERGENCY ROLLBACK for client {client_id}. Reason: {reason}")
    
    result = {
        "client_id": client_id,
        "rollback_id": f"rollback_{client_id}_{int(time.time())}",
        "timestamp": datetime.now().isoformat(),
        "status": "rolled_back",
        "previous_version": "v1.2.3",
        "reason": reason,
        "message": "Successfully rolled back to previous stable version."
    }
    
    return json.dumps(result, indent=2)