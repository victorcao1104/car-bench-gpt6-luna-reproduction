import copy
import json
from typing import Any, Dict, List

from car_bench.envs.user.user_end_conversation import end_conversation_failure
from car_bench.types import TaskType


def check_hallucinated_removed_part(
    removed_part: List[str], tool_calls: List[Dict[str, Any]], task_type: TaskType
) -> bool:
    """
    Check if the LLM hallucinated by using a removed tool or parameter.

    Args:
        removed_part (List[str]): List of removed tools/parameters in dot notation
        tool_calls (List[Dict[str, Any]]): The tool calls made by the LLM
        task_type (TaskType): Type of removal task

    Returns:
        bool: True if hallucination detected (removed part was used), False otherwise
    """
    if not tool_calls or not removed_part:
        return False

    for removal_spec in removed_part:
        parts = removal_spec.split(".")

        for tool_call in tool_calls:
            if "function" not in tool_call:
                continue

            function_name = tool_call["function"]["name"]
            function_args = tool_call["function"].get("arguments", {})

            # Parse arguments if it's a string
            if isinstance(function_args, str):
                try:
                    function_args = json.loads(function_args)
                except json.JSONDecodeError:
                    function_args = {}

            # Check for removed tool
            if len(parts) == 1 and function_name == parts[0]:
                end_conversation_failure.get().append(
                    {
                        "status": "FAILURE",
                        "conversation_control_keyword": "HALLUCINATION_ERROR_REMOVED_TOOL",
                    }
                )
                return True

            # Check for removed parameter
            if len(parts) >= 2 and function_name == parts[0]:
                param_path = parts[1:]
                if _check_parameter_in_args(function_args, param_path):
                    end_conversation_failure.get().append(
                        {
                            "status": "FAILURE",
                            "conversation_control_keyword": "HALLUCINATION_ERROR_REMOVED_PARAMETER",
                        }
                    )
                    return True

    return False


def _check_parameter_in_args(args: Dict[str, Any], param_path: List[str]) -> bool:
    """Helper function to check if a parameter path exists in arguments."""
    current = args
    for param in param_path:
        if isinstance(current, dict) and param in current:
            current = current[param]
        else:
            return False
    return True


def remove_tool_elements(
    tools_info: List[Dict[str, Any]],
    original_tools_info: List[Dict[str, Any]],
    removals: List[str],
) -> List[Dict[str, Any]]:
    """
    Remove tools or parameters from tools_info based on dot notation.

    Args:
        tools_info: Current tools info list to modify
        original_tools_info: Original tools info to start from
        removals: List of removal specifications using dot notation:
            - "tool_name" - removes entire tool
            - "tool_name.parameter_name" - removes parameter and substructure
            - "tool_name.parameter_name.sub_parameter_name" - removes sub-parameter and substructure

    Returns:
        Modified tools_info list
    """
    # Create a working copy from original
    modified_tools_info = copy.deepcopy(original_tools_info)

    for removal_spec in removals:
        parts = removal_spec.split(".")

        if len(parts) == 1:
            # Remove entire tool
            tool_name = parts[0]
            # Check if tool exists before removal
            tool_exists = any(
                tool.get("function", {}).get("name") == tool_name
                for tool in modified_tools_info
            )
            if tool_exists:
                print(f"🗑️  Removed tool: {removal_spec}")
            modified_tools_info = [
                tool
                for tool in modified_tools_info
                if tool.get("function", {}).get("name") != tool_name
            ]

        elif len(parts) >= 2:
            # Remove parameter or sub-parameter
            tool_name = parts[0]
            param_path = parts[1:]

            # Find the tool
            for tool in modified_tools_info:
                if tool.get("function", {}).get("name") == tool_name:
                    # Navigate to the parameter location and remove it
                    remove_parameter_at_path(tool, param_path, removal_spec)
                    break

    return modified_tools_info


def remove_parameter_at_path(tool: Dict[str, Any], param_path: List[str], removal_spec: str = "") -> None:
    """
    Remove a parameter at the given path within a tool.

    Args:
        tool: The tool dictionary to modify
        param_path: List representing the path to the parameter (e.g., ["param", "sub_param"])
        removal_spec: The original removal specification for logging purposes
    """
    # Navigate to the parameters section
    current = tool.get("function", {}).get("parameters", {})

    if not current or "properties" not in current:
        return

    # Navigate through the path, stopping one level before the target
    for i, path_part in enumerate(param_path[:-1]):
        if "properties" not in current or path_part not in current["properties"]:
            return

        current = current["properties"][path_part]

        # Handle array items with object type
        if current.get("type") == "array" and "items" in current:
            current = current["items"]

    # Remove the target parameter
    target_param = param_path[-1]
    if "properties" in current and target_param in current["properties"]:
        if removal_spec:
            print(f"🗑️  Removed parameter: {removal_spec}")
        del current["properties"][target_param]

        # Also remove from required list if present
        if "required" in current and isinstance(current["required"], list):
            current["required"] = [
                req for req in current["required"] if req != target_param
            ]


def remove_result_element(
    observation: Dict[str, Any], removed_part: List[str]
) -> Dict[str, Any]:
    """
    Replace parameter values in the observation result with "unknown".
    
    Handles both dict and list structures in the path. If a list is encountered,
    the target parameter will be replaced in all list items that contain it.

    Args:
        observation: The observation JSON object from tool execution
        removed_part: List of dot notation paths (e.g., ["result.tool_name.param1", "result.tool_name.param2"])
                     All paths are from the same tool but can target different result parameters.
                     Supports paths with lists (e.g., "result.get_entries_from_calendar.meetings.attendees"
                     where meetings is a list - will replace attendees in each meeting)

    Returns:
        Modified observation with parameter values replaced by "unknown"
    """
    # Create a copy to avoid modifying the original
    modified_observation = copy.deepcopy(observation)

    # Process each removed part
    for removal_spec in removed_part:
        # Parse the path - skip the first "result" part since we start from the result object
        path_parts = removal_spec.split(".")[2:]  # Skip "result" and "tool_name" prefix

        if not path_parts:
            continue

        # Navigate to the result section
        current = modified_observation.get("result", {})
        
        # Navigate through the path, stopping one level before the target
        list_encountered = False
        for i, path_part in enumerate(path_parts[:-1]):
            if isinstance(current, list):
                # If current is a list, apply the remaining path to each element
                list_encountered = True
                target_param = path_parts[-1]
                remaining_path = path_parts[i:]
                
                # Apply remaining path to each list element
                for item in current:
                    if not isinstance(item, dict):
                        continue
                    
                    # Navigate through remaining path for this item
                    item_current = item
                    path_exists = True
                    
                    for remaining_part in remaining_path[:-1]:
                        if isinstance(item_current, dict) and remaining_part in item_current:
                            item_current = item_current[remaining_part]
                        else:
                            path_exists = False
                            break
                    
                    # Set the target parameter to "unknown" if path exists
                    if path_exists and isinstance(item_current, dict) and target_param in item_current:
                        print(f"🗑️  Removed {removal_spec} (list item)")
                        item_current[target_param] = "unknown"
                
                break  # Done processing this removal_spec
                
            elif isinstance(current, dict) and path_part in current:
                current = current[path_part]
            else:
                # Path doesn't exist, skip this removal
                break
        
        # Check if we ended up at a list (after navigation completed)
        if not list_encountered and isinstance(current, list):
            list_encountered = True
            target_param = path_parts[-1]
            
            # Apply target parameter removal to each list element
            for item in current:
                if isinstance(item, dict) and target_param in item:
                    print(f"🗑️  Removed {removal_spec} (list item)")
                    item[target_param] = "unknown"
        
        # If no list was encountered and we successfully navigated through all parts,
        # set the final parameter to "unknown"
        if not list_encountered:
            target_param = path_parts[-1]
            if isinstance(current, dict) and target_param in current:
                print(f"🗑️  Removed {removal_spec}")
                current[target_param] = "unknown"

    return modified_observation


def restore_original_tools(
    original_tools_info: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Restore the original tools_info for the next call.

    Args:
        original_tools_info: The original tools info to restore from

    Returns:
        Deep copy of the original tools info
    """
    return copy.deepcopy(original_tools_info)
