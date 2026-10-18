import json
from typing import Any, Dict, Union

from car_bench.envs.car_voice_assistant.context.fixed_context import fixed_context
from car_bench.envs.tool import Tool


class GetCarColor(Tool):
    "Vehicle Information: Get the outside color of the car."

    @staticmethod
    def invoke(data: Dict[str, Any]) -> Dict[str, Union[str, None]]:
        """
        Returns:
            status (str): Indicates if the tool call was a "SUCCESS" or "FAILURE".
            result (dict): Contains the color of the car.
        """
        fixed_ctx = fixed_context.get()
        response = {}

        car_color = fixed_ctx.car_color

        response["status"] = "SUCCESS"
        response["result"] = {"car_color": car_color}
        return json.dumps(response)

    @staticmethod
    def get_info() -> Dict[str, Any]:
        """
        Tool description visible to LLM.
        """

        return {
            "type": "function",
            "function": {
                "name": "get_car_color",
                "description": "Vehicle Information: Get the outside color of the car.",
                # "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {},
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
                "car_color": {
                    "type": "string",
                    "description": "The outside color of the car.",
                    "examples": ["blue"],
                }
            },
            "required": ["car_color"],
            "additionalProperties": False,
        }
