import json
from open_learning_ai_tutor.constants import Intent


def json_to_intent_list(json_str):
    """Convert a JSON string to a list of Intent enums."""
    intent_lists = json.loads(json_str)
    return [
        [Intent[name] for name in intent_names if name in Intent.__members__]
        for intent_names in intent_lists
    ]


def intent_list_to_json(intent_lists):
    """Convert a list of Intent enums to a JSON string."""
    intent_names = [
        [intent.name for intent in intent_list] for intent_list in intent_lists
    ]
    return json.dumps(intent_names)


def print_logs(log):
    print("--------\n")
    for msg in log:
        print(msg)
    print("--------\n")


def generate_messages(student_messages, tutor_messages, init_message, role):
    if role == "student":
        roles = ["user", "assistant"]
    else:
        roles = ["assistant", "user"]

    messages = [{"role": "system", "content": init_message}]

    for i in range(min(len(student_messages), len(tutor_messages))):

        messages.append({"role": roles[0], "content": tutor_messages[i]})
        messages.append({"role": roles[1], "content": student_messages[i]})

    if role == "student" and len(student_messages) < len(tutor_messages):
        messages.append({"role": "user", "content": tutor_messages[-1]})
    elif role == "tutor" and len(student_messages) > len(tutor_messages):
        messages.append({"role": "user", "content": student_messages[-1]})

    return messages


def messages_to_json(messages):
    """
    Convert a list of LangChain message objects to JSON format.

    Args:
        messages: List of LangChain message objects (AIMessage, HumanMessage, ToolMessage, etc.)

    Returns:
        list: List of dictionaries containing message data
    """
    json_messages = []

    for message in messages:
        message_dict = {"type": message.__class__.__name__, "content": message.content}

        # Add additional fields if they exist
        if hasattr(message, "additional_kwargs"):
            message_dict.update(message.additional_kwargs)

        if hasattr(message, "name") and message.name:
            message_dict["name"] = message.name

        # Add special fields for specific message types
        if hasattr(message, "tool_call_id"):
            message_dict["tool_call_id"] = message.tool_call_id

        if hasattr(message, "role"):
            message_dict["role"] = message.role

        json_messages.append(message_dict)

    return json_messages


def json_to_messages(json_messages):
    """
    Convert JSON format back to LangChain message objects.

    Args:
        json_messages: List of dictionaries containing message data

    Returns:
        list: List of LangChain message objects
    """
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
        FunctionMessage,
        ChatMessage,
    )

    message_type_map = {
        "AIMessage": AIMessage,
        "HumanMessage": HumanMessage,
        "SystemMessage": SystemMessage,
        "ToolMessage": ToolMessage,
        "FunctionMessage": FunctionMessage,
        "ChatMessage": ChatMessage,
    }

    messages = []

    for msg in json_messages:
        msg_type = msg["type"]
        msg_content = msg["content"]

        # Get the message class from the type
        message_class = message_type_map.get(msg_type)
        if not message_class:
            raise ValueError(f"Unknown message type: {msg_type}")

        # Extract special fields
        tool_call_id = msg.get("tool_call_id")
        name = msg.get("name")
        role = msg.get("role")

        # Extract additional kwargs, excluding special fields
        additional_kwargs = {
            k: v
            for k, v in msg.items()
            if k not in ["type", "content", "name", "tool_call_id", "role"]
        }

        # Create kwargs dict with only existing values
        kwargs = {"content": msg_content}
        if additional_kwargs:
            kwargs["additional_kwargs"] = additional_kwargs
        if name:
            kwargs["name"] = name
        if tool_call_id:
            kwargs["tool_call_id"] = tool_call_id
        if role:
            kwargs["role"] = role

        # Create the message object
        message = message_class(**kwargs)
        messages.append(message)

    return messages


# def test_message_conversions():
#     """
#     Test the message conversion functions by converting LangChain messages to JSON
#     and back, verifying that the result matches the original input.
#     """
#     from langchain_core.messages import (
#         AIMessage,
#         HumanMessage,
#         SystemMessage,
#         ToolMessage,
#         FunctionMessage,
#         ChatMessage
#     )

#     # Create test messages with various features
#     test_messages = [
#         HumanMessage(content="Hello!"),
#         AIMessage(
#             content="Hi there!",
#             additional_kwargs={"metadata": {"confidence": 0.9}}
#         ),
#         SystemMessage(content="You are a helpful assistant"),
#         ToolMessage(
#             content="42",
#             tool_call_id="call_123",
#             name="calculator",
#             additional_kwargs={"tool_metadata": {"precision": "high"}}
#         ),
#         FunctionMessage(
#             content="Function result",
#             name="get_weather",
#             additional_kwargs={"temperature": 72}
#         ),
#         ChatMessage(
#             content="General chat message",
#             role="user",
#             additional_kwargs={"custom_field": "value"}
#         )
#     ]

#     # Convert to JSON
#     json_messages = messages_to_json(test_messages)

#     # Convert back to LangChain messages
#     converted_messages = json_to_messages(json_messages)

#     # Verify the conversion
#     assert len(test_messages) == len(converted_messages), "Message count mismatch"

#     for original, converted in zip(test_messages, converted_messages):
#         # Check type
#         assert type(original) == type(converted), f"Type mismatch: {type(original)} != {type(converted)}"

#         # Check content
#         assert original.content == converted.content, f"Content mismatch: {original.content} != {converted.content}"

#         # Check name if exists
#         if hasattr(original, 'name'):
#             assert original.name == converted.name, f"Name mismatch: {original.name} != {converted.name}"

#         # Check additional kwargs
#         assert original.additional_kwargs == converted.additional_kwargs, \
#             f"Additional kwargs mismatch: {original.additional_kwargs} != {converted.additional_kwargs}"

#     print("All tests passed successfully!")
#     return True

# test_message_conversions()
