import pytest
from open_learning_ai_tutor.assessor import Assessor, get_inital_prompt
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


async def test_assessor_graph(mocker):
    """Test that the Assessor class creates a graph with the correct nodes and edges."""
    mock_client = mocker.MagicMock()
    assessor = Assessor(mock_client, [], [])
    app = assessor.app
    for node in ("agent", "tools"):
        assert node in app.nodes
    graph = app.get_graph()

    edges = graph.edges
    assert len(edges) == 4
    tool_agent_edge = edges[1]
    for test_condition in (
        tool_agent_edge.source == "tools",
        tool_agent_edge.target == "agent",
        not tool_agent_edge.conditional,
    ):
        assert test_condition
    agent_tool_edge = edges[2]
    for test_condition in (
        agent_tool_edge.source == "agent",
        agent_tool_edge.target == "tools",
        agent_tool_edge.conditional,
    ):
        assert test_condition
    agent_end_edge = edges[3]
    for test_condition in (
        agent_end_edge.source == "agent",
        agent_end_edge.target == "__end__",
        agent_end_edge.conditional,
    ):
        assert test_condition


@pytest.mark.parametrize("existing_assessment_history", [True, False])
async def test_create_prompt(mocker, existing_assessment_history):
    """Test that the Assessor create_prompt method returns the correct prompt."""
    mock_client = mocker.MagicMock()
    if existing_assessment_history:
        assessment_history = [
            HumanMessage(content=' Student: "what do i do next?"'),
            AIMessage(
                content='{\n    "justification": "The student is explicitly asking for guidance on how to proceed with solving the problem, indicating they are unsure of the next steps.",\n    "selection": "g"\n}'
            ),
        ]
    else:
        assessment_history = []

    new_messages = [HumanMessage(content="what if i took the mean?")]
    assessor = Assessor(mock_client, assessment_history, new_messages)

    problem = "problem"
    problem_set = "problem_set"

    prompt = assessor.create_prompt(problem, problem_set)

    initial_prompt = SystemMessage(get_inital_prompt(problem, problem_set))
    new_messages_prompt_part = HumanMessage(
        content=' Student: "what if i took the mean?"'
    )

    if existing_assessment_history:
        expected_prompt = [
            initial_prompt,
            *assessment_history,
            new_messages_prompt_part,
        ]
    else:
        expected_prompt = [initial_prompt, new_messages_prompt_part]
    assert prompt == expected_prompt
