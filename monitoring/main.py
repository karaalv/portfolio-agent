"""
This module acts as the main interface for
monitoring processes.
"""
import hashlib
import textwrap
from datetime import timedelta
from typing import Any
from monitoring.schemas import UserUsage
from common.utils import handle_exceptions_async, handle_exceptions
from common.utils import TerminalColors, get_timestamp, get_datetime
from database.mongodb.main import get_collection
from openai_client.main import normal_response

# --- Constants ---

USAGE_LIMIT = 5 # Number of generations allowed weekly

# --- Utility Functions ---

@handle_exceptions("monitoring.main: Generating usage ID")
def generate_usage_id(
    ip: str, ua: str,
):
    """
    Generate a unique usage ID based on the 
    user's IP address and user agent.
    """
    hash_input = f"{ip}-{ua}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

# --- Creation ---

@handle_exceptions_async("monitoring.main: Create User Usage")
async def _create_user_usage(
    user_id: str, ip: str, ua: str
) -> UserUsage:
    """
    Create a new user usage record.
    """
    usage_id = generate_usage_id(ip, ua)
    collection = get_collection("monitoring")

    user_usage = UserUsage(
        user_id=user_id,
        usage_id=usage_id,
        ip=ip,
        generation_count=1,
        total_generations=1,
        latest_generation=get_timestamp()
    )

    await collection.insert_one(user_usage.model_dump())
    return user_usage

# --- Retrieval ---

@handle_exceptions_async("monitoring.main: Get User Usage")
async def get_user_usage(usage_id: str) -> UserUsage | None:
    """
    Retrieve a user usage record by usage ID.
    """
    collection = get_collection("monitoring")
    result = await collection.find_one({"usage_id": usage_id})
    if result:
        return UserUsage.model_validate(result)
    return None

# --- Inspection ---

@handle_exceptions_async("monitoring.main: Does Usage ID Exist")
async def does_usage_id_exist(usage_id: str) -> bool:
    """
    Check if a user usage record exists by usage ID.
    """
    collection = get_collection("monitoring")
    result = await collection.find_one({"usage_id": usage_id})
    return result is not None

@handle_exceptions_async("monitoring.main: Check Usage Limit")
async def check_usage_limit(
    user_id: str,
    ip: str,
    ua: str
) -> bool:
    """
    Checks if user has exceeded their usage limit.
    """
    usage_id = generate_usage_id(ip, ua)
    
    if not await does_usage_id_exist(usage_id):
        await _create_user_usage(user_id, ip, ua)
        return True
    
    collection = get_collection("monitoring")
    
    # Check time since last generation
    data = await get_user_usage(usage_id)
    usage_record = UserUsage.model_validate(data)
    delta = get_datetime() - get_datetime(usage_record.latest_generation)

    if delta > timedelta(weeks=1):
        # Reset the usage count
        await collection.update_one(
            {"usage_id": usage_id},
            {"$set": {
                    "generation_count": 1, 
                    "latest_generation": get_timestamp()
                }
            }
        )
        return True

    result = await collection.update_one(
        {
            "usage_id": usage_id,
            "generation_count": {"$lt": USAGE_LIMIT}
        },
        {
            "$inc": {"generation_count": 1, "total_generations": 1},
            "$set": {"latest_generation": get_timestamp()}
        }
    )

    if result.modified_count == 0:
        # User has hit their usage limit
        return False

    return True

@handle_exceptions_async("monitoring.main: Get Usages Remaining")
async def get_usages_remaining(ip: str, ua: str) -> int:
    """
    Get the number of usages remaining for a user.
    """
    usage_id = generate_usage_id(ip, ua)
    collection = get_collection("monitoring")
    data = await collection.find_one({"usage_id": usage_id})
    usage_info: dict[str, Any] = data # type: ignore

    if not usage_info:
        return USAGE_LIMIT

    return USAGE_LIMIT - usage_info['generation_count']

# --- Warnings ---

@handle_exceptions_async("monitoring.main: Inform User Usage Limit")
async def inform_user_usage_limit() -> str:
    """
    This function sends a message to the user
    informing them that they have reached their
    usage limit for generation tasks.
    """
    system_prompt = textwrap.dedent("""
        You are impersonating Alvin Karanja on his portfolio 
        site. Respond in the first person, directly to the 
        user, in a single concise message. 

        Inform them that they've reached their limit for 
        generating resumes and cover letters. Clarify that 
        they can still chat with you for regular Q&A, but 
        won't be able to generate new documents until their 
        usage limit resets in 1 week.

        Do not greet the user or add any unnecessary 
        commentary, simply inform the user that they have 
        reached their limit.
    """)

    return await normal_response(
        system_prompt=system_prompt,
        user_input="Obey the system prompt.",
    )
