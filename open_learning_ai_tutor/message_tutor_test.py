import pytest
from open_learning_ai_tutor.message_tutor import message_tutor
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from open_learning_ai_tutor.constants import Intent


def test_message_tutor(mocker):
    """Test message_tutor function with no A/B testing"""
    # Mock ACTIVE_AB_TESTS to be empty (no A/B tests active)
    mocker.patch("open_learning_ai_tutor.prompts.ACTIVE_AB_TESTS", {})

    assessment_response = {
        "messages": [
            SystemMessage(content="problem prompt"),
            HumanMessage(content='Student: "what should i try first"'),
            AIMessage(content='{"justification": "test", "selection": "g"}'),
        ]
    }

    tutor_response = "a generator with tutor response"

    # Mock the Tutor class
    mock_tutor = mocker.patch("open_learning_ai_tutor.message_tutor.Tutor")
    mock_tutor_instance = mock_tutor.return_value

    # Configure the async mock response
    mock_get_response = mocker.Mock()
    mock_get_response.return_value = assessment_response

    mock_streaming_response = mocker.Mock()
    mock_streaming_response.return_value = tutor_response

    mock_tutor_instance.get_response = mock_get_response
    mock_tutor_instance.get_streaming_response = mock_streaming_response
    
    # Mock get_tutor_prompt to return non-A/B test result
    mock_get_tutor_prompt = mocker.patch("open_learning_ai_tutor.message_tutor.get_tutor_prompt")
    mock_get_tutor_prompt.return_value = {
        "is_ab_test": False,
        "prompt": [SystemMessage(content="mocked prompt")]
    }

    problem = "problem"
    problem_set = "problem_set"
    client = mocker.Mock()
    client.model_name = "test_model"
    new_messages = [HumanMessage(content="what should i try first")]
    chat_history = [HumanMessage(content="what should i try first")]
    assessment_history = [
        HumanMessage(content='Student: "i am confused"'),
        AIMessage(content='{"justification": "test", "selection": "c"}'),
    ]
    intent_history = []
    tools = []

    response = message_tutor(
        problem,
        problem_set,
        client,
        new_messages,
        chat_history,
        assessment_history,
        intent_history,
        tools=tools,
    )

    # Assertions for non-A/B test response
    assert response == (
        tutor_response,
        [
            [Intent.P_HYPOTHESIS],
        ],
        [
            HumanMessage(
                content='Student: "i am confused"',
                additional_kwargs={},
                response_metadata={},
            ),
            AIMessage(
                content='{"justification": "test", "selection": "c"}',
                additional_kwargs={},
                response_metadata={},
            ),
            HumanMessage(
                content='Student: "what should i try first"',
                additional_kwargs={},
                response_metadata={},
            ),
            AIMessage(
                content='{"justification": "test", "selection": "g"}',
                additional_kwargs={},
                response_metadata={},
            ),
        ],
    )
    assert mock_get_response.call_count == 1
    assert mock_streaming_response.call_count == 1


def test_message_tutor_ab_testing(mocker):
    """Test message_tutor function with A/B testing enabled"""
    # Mock ACTIVE_AB_TESTS to have A/B testing active
    mocker.patch("open_learning_ai_tutor.prompts.ACTIVE_AB_TESTS", {
        "tutor_problem": {
            "variants": ["tutor_problem_v1", "tutor_problem_v2"],
            "probability": 1  # Always activate A/B test
        }
    })

    assessment_response = {
        "messages": [
            SystemMessage(content="problem prompt"),
            HumanMessage(content='Student: "what should i try first"'),
            AIMessage(content='{"justification": "test", "selection": "g"}'),
        ]
    }

    control_response = "control response generator"
    treatment_response = "treatment response generator"

    # Mock the Tutor class
    mock_tutor = mocker.patch("open_learning_ai_tutor.message_tutor.Tutor")
    mock_tutor_instance = mock_tutor.return_value

    # Configure the mock responses
    mock_get_response = mocker.Mock()
    mock_get_response.return_value = assessment_response

    mock_streaming_response = mocker.Mock()
    mock_streaming_response.side_effect = [control_response, treatment_response]

    mock_tutor_instance.get_response = mock_get_response
    mock_tutor_instance.get_streaming_response = mock_streaming_response

    problem = "problem"
    problem_set = "problem_set"
    client = mocker.Mock()
    client.model_name = "test_model"
    new_messages = [HumanMessage(content="what should i try first")]
    chat_history = [HumanMessage(content="what should i try first")]
    assessment_history = [
        HumanMessage(content='Student: "i am confused"'),
        AIMessage(content='{"justification": "test", "selection": "c"}'),
    ]
    intent_history = []
    tools = []

    response = message_tutor(
        problem,
        problem_set,
        client,
        new_messages,
        chat_history,
        assessment_history,
        intent_history,
        tools=tools,
    )

    # Assertions for A/B test response
    tutor_response, new_intent_history, new_assessment_history = response
    
    # Check A/B test structure
    assert isinstance(tutor_response, dict)
    assert tutor_response["is_ab_test"] == True
    assert "responses" in tutor_response
    assert len(tutor_response["responses"]) == 2
    
    # Check response structure
    responses = tutor_response["responses"]
    assert responses[0]["variant"] == "control"
    assert responses[0]["stream"] == control_response
    assert responses[1]["variant"] == "treatment"
    assert responses[1]["stream"] == treatment_response
    
    # Check intent and assessment histories are the same regardless of A/B test
    assert new_intent_history == [[Intent.P_HYPOTHESIS]]
    assert new_assessment_history == [
        HumanMessage(
            content='Student: "i am confused"',
            additional_kwargs={},
            response_metadata={},
        ),
        AIMessage(
            content='{"justification": "test", "selection": "c"}',
            additional_kwargs={},
            response_metadata={},
        ),
        HumanMessage(
            content='Student: "what should i try first"',
            additional_kwargs={},
            response_metadata={},
        ),
        AIMessage(
            content='{"justification": "test", "selection": "g"}',
            additional_kwargs={},
            response_metadata={},
        ),
    ]
    
    assert mock_get_response.call_count == 1
    assert mock_streaming_response.call_count == 2  # Called twice for control and treatment


def test_message_tutor_ab_testing(mocker):
    """Test message_tutor function with A/B testing enabled"""

    assessment_response = {
        "messages": [
            SystemMessage(content="problem prompt"),
            HumanMessage(content='Student: "what should i try first"'),
            AIMessage(content='{"justification": "test", "selection": "g"}'),
        ]
    }

    control_response = "control response generator"
    treatment_response = "treatment response generator"

    # Mock the Tutor class
    mock_tutor = mocker.patch("open_learning_ai_tutor.message_tutor.Tutor")
    mock_tutor_instance = mock_tutor.return_value

    # Configure the mock responses
    mock_get_response = mocker.Mock()
    mock_get_response.return_value = assessment_response

    mock_streaming_response = mocker.Mock()
    mock_streaming_response.side_effect = [control_response, treatment_response]

    mock_tutor_instance.get_response = mock_get_response
    mock_tutor_instance.get_streaming_response = mock_streaming_response
    
    # Mock get_tutor_prompt to return A/B test result
    mock_get_tutor_prompt = mocker.patch("open_learning_ai_tutor.message_tutor.get_tutor_prompt")
    mock_get_tutor_prompt.return_value = {
        "is_ab_test": True,
        "control": [SystemMessage(content="control prompt")],
        "treatment": [SystemMessage(content="treatment prompt")]
    }

    problem = "problem"
    problem_set = "problem_set"
    client = mocker.Mock()
    client.model_name = "test_model"
    new_messages = [HumanMessage(content="what should i try first")]
    chat_history = [HumanMessage(content="what should i try first")]
    assessment_history = [
        HumanMessage(content='Student: "i am confused"'),
        AIMessage(content='{"justification": "test", "selection": "c"}'),
    ]
    intent_history = []
    tools = []

    response = message_tutor(
        problem,
        problem_set,
        client,
        new_messages,
        chat_history,
        assessment_history,
        intent_history,
        tools=tools,
    )

    # Assertions for A/B test response
    expected_response = (
        {
            "is_ab_test": True,
            "responses": [
                {"variant": "control", "stream": control_response},
                {"variant": "treatment", "stream": treatment_response}
            ]
        },
        [
            [Intent.P_HYPOTHESIS],
        ],
        [
            HumanMessage(
                content='Student: "i am confused"',
                additional_kwargs={},
                response_metadata={},
            ),
            AIMessage(
                content='{"justification": "test", "selection": "c"}',
                additional_kwargs={},
                response_metadata={},
            ),
            HumanMessage(
                content='Student: "what should i try first"',
                additional_kwargs={},
                response_metadata={},
            ),
            AIMessage(
                content='{"justification": "test", "selection": "g"}',
                additional_kwargs={},
                response_metadata={},
            ),
        ],
    )
    
    assert response == expected_response
    assert mock_get_response.call_count == 1
    assert mock_streaming_response.call_count == 2  # Called twice for control and treatment
