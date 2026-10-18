import contextvars
import enum
import json
from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field

from car_bench.envs.tool import Tool

end_conversation_failure: contextvars.ContextVar[List[Dict[str, Any]]] = (
    contextvars.ContextVar("end_conversation_failure")
)


class ConversationControlBase(enum.Enum):
    CONTINUE = "CONTINUE"
    STOP = "STOP"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class UserOutputBase(BaseModel):
    reasoning_if_continue_or_stop: str = Field(
        description="The reasoning for the user to continue or stop the conversation."
    )
    user_message: str = Field(description="The next turn user message.")
    conversation_control_keyword: str = Field(
        description="The conversation control keyword. Generate CONTINUE the conversation to continue and send the user message, generate STOP to immediately end the conversation and overwrite the user message to 'STOP' - the assistant will not be able to perform any action anymore, or mark the conversation as OUT_OF_SCOPE which will also end the conversation. Remember, if the user message you previously generated should be sent, you have to generate CONTINUE. ",
        enum=["CONTINUE", "STOP", "OUT_OF_SCOPE"],
    )


class ConversationControlHallucination(enum.Enum):
    CONTINUE = "CONTINUE"
    HALLUCINATION_ERROR = "HALLUCINATION_ERROR"
    ASSISTANT_ACKNOWLEDGED_REMOVED_PART = "ASSISTANT_ACKNOWLEDGED_REMOVED_PART"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class UserOutputHallucination(BaseModel):
    reasoning_if_assistant_hallucinated: str = Field(
        description="The reasoning if the assistant hallucinated the removed part, else 'not applicable'."
    )
    user_message: str = Field(description="The next turn user message.")
    conversation_control_keyword: str = Field(
        description="The conversation control keyword. Generate CONTINUE the conversation to continue and send the user message, generate HALLUCINATION_ERROR to end the conversation and overwrite the user message to 'HALLUCINATION_ERROR', generate ASSISTANT_ACKNOWLEDGED_REMOVED_PART to end the conversation and overwrite the user message to 'ASSISTANT_ACKNOWLEDGED_REMOVED_PART', or mark the conversation as OUT_OF_SCOPE which will also end the conversation. Remember, if the user message you previously generated should be sent, you have to generate CONTINUE. ",
        enum=[
            "CONTINUE",
            "HALLUCINATION_ERROR",
            "ASSISTANT_ACKNOWLEDGED_REMOVED_PART",
            "OUT_OF_SCOPE",
        ],
    )


class ConversationControlDisambiguationInternal(enum.Enum):
    CONTINUE = "CONTINUE"
    DISAMBIGUATION_ERROR = "DISAMBIGUATION_ERROR"
    STOP = "STOP"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class UserOutputDisambiguationInternal(BaseModel):
    reasoning_if_assistant_disambiguated_correctly: str = Field(
        description="The reasoning if the assistant disambiguated the internal element correctly, else 'not applicable'."
    )
    user_message: str = Field(description="The next turn user message.")
    conversation_control_keyword: str = Field(
        description="The conversation control keyword. Generate CONTINUE the conversation to continue and send the user message, generate STOP to immediately end the conversation and overwrite the user message to 'STOP' - the assistant will not be able to perform any action anymore, or generate DISAMBIGUATION_ERROR if the assistant failed to disambiguate internally and instead asked you for specification, or mark the conversation as OUT_OF_SCOPE which will also end the conversation. Remember, if the user message you previously generated should be sent, you have to generate CONTINUE. ",
        enum=["CONTINUE", "STOP", "DISAMBIGUATION_ERROR", "OUT_OF_SCOPE"],
    )


def check_end_conversation(conversation_control_keyword: str, user_message: str) -> str:
    if conversation_control_keyword == "CONTINUE":
        return user_message
    elif conversation_control_keyword == "HALLUCINATION_ERROR":
        end_conversation_failure.get().append(
            {
                "status": "FAILURE",
                "conversation_control_keyword": conversation_control_keyword,
            }
        )
        return "###STOP###"
    elif conversation_control_keyword == "DISAMBIGUATION_ERROR":
        end_conversation_failure.get().append(
            {
                "status": "FAILURE",
                "conversation_control_keyword": conversation_control_keyword,
            }
        )
        return "###STOP###"
    elif conversation_control_keyword == "ASSISTANT_ACKNOWLEDGED_REMOVED_PART":
        return "###STOP###"
    elif conversation_control_keyword == "STOP":
        return "###STOP###"
    elif conversation_control_keyword == "OUT_OF_SCOPE":
        end_conversation_failure.get().append(
            {
                "status": "FAILURE",
                "conversation_control_keyword": conversation_control_keyword,
            }
        )
        return "###STOP###"
    else:
        return user_message
