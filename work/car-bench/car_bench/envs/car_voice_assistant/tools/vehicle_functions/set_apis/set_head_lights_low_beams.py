import json
from typing import Any, Dict, Literal, TypeAlias, Union

from pydantic import BaseModel, Field

from car_bench.envs.car_voice_assistant.context.dynamic_context_state import (
    context_state,
)
from car_bench.envs.tool import Tool


class SetHeadLightsLowBeams(Tool):
    "Vehicle Control: Turns the low beam headlights outside the car on or off."

    @staticmethod
    def invoke(data: Dict[str, Any], on: bool) -> Dict[str, Union[str, None]]:
        """
        Args:
            on (bool): True to turn on the low beam headlights, False to turn off the low beam headlights.
        Returns:
            status (str): Indicates if the tool call was a "SUCCESS" or "FAILURE".
        """
        vehicle_ctx = context_state.get()
        response = {}

        response["status"] = "SUCCESS"
        response["result"] = {"on": on}
        vehicle_ctx.update_state(head_lights_low_beams=on)

        return json.dumps(response)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        """
        Tool description visible to LLM.
        """

        return {
            "type": "function",
            "function": {
                "name": "set_head_lights_low_beams",
                "description": "Vehicle Control: Turns the low beam headlights outside the car on or off.",
                # "strict": True,
                "parameters": {
                    "type": "object",
                    "required": ["on"],
                    "properties": {
                        "on": {
                            "type": "boolean",
                            "description": "True to turn on the low beam headlights, False to turn off the low beam headlights.",
                        }
                    },
                    "additionalProperties": False,
                },
            },
        }

    @staticmethod
    def get_output_info() -> Dict[str, Any]:
        """
        Output variable description
        """
        return {
            "type": "object",
            "properties": {
                "on": {
                    "type": "boolean",
                    "description": "Indicates whether the low beam headlights were turned on (true) or off (false).",
                    "examples": [False],
                }
            },
            "required": ["on"],
            "additionalProperties": False,
        }
