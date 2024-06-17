from typing import Optional

import pytest

from langroid import ChatDocument
from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig
from langroid.agent.task import Task
from langroid.parsing.routing import parse_addressed_message
from langroid.utils.configuration import Settings, set_global
from langroid.utils.constants import AT, DONE, SEND_TO

ADDRESSES = [
    AT + "Alice ",
    AT + "Alice,",
    AT + "Alice:",
    f"{SEND_TO}Alice ",
    f"{SEND_TO}Alice:",
    f"{SEND_TO}Alice,",
]


@pytest.mark.parametrize("address", ADDRESSES)
def test_parse_address(address: str):
    """Test that the address is parsed correctly."""
    msg = f"ok @all, @xyz here is my message to {address} -- {address} Hello"
    (addressee, content) = parse_addressed_message(
        msg,
        addressing="@" if AT in address else SEND_TO,
    )
    assert addressee == "Alice"
    assert content == "Hello"


@pytest.mark.parametrize(
    "address",
    ADDRESSES,
)
@pytest.mark.parametrize("x,answer", [(5, 25)])
def test_addressing(test_settings: Settings, address: str, x: int, answer: int):
    """Test that an agent is able to address another agent in a message."""
    set_global(test_settings)

    class BobAgent(ChatAgent):
        def llm_response(
            self, message: Optional[str | ChatDocument] = None
        ) -> Optional[ChatDocument]:
            if (
                isinstance(message, ChatDocument)
                and message.metadata.sender_name == "Alice"
            ):
                return self.create_llm_response(DONE + " " + message.content)

            addr = "@" if AT in address else SEND_TO
            # throw in some distracting addresses, to test that
            # only the last one is picked up
            return self.create_llm_response(
                f"Ok {addr}all here {addr}Junk is my question: {address} {x}"
            )

    class AliceAgent(ChatAgent):
        def llm_response(
            self, message: Optional[str | ChatDocument] = None
        ) -> Optional[ChatDocument]:
            y = int(message.content.strip())
            answer = y * y
            return self.create_llm_response(f"{DONE} {answer}")

    bob_config = ChatAgentConfig(name="Bob")

    bob = BobAgent(bob_config)
    # When addressing Alice, set it to non-interactive, else interactive
    bob_task = Task(bob, interactive=False)

    alice_config = ChatAgentConfig(name="Alice")
    alice = AliceAgent(alice_config)
    alice_task = Task(alice, interactive=False)

    bob_task.add_sub_task(alice_task)

    result = bob_task.run()
    assert answer == int(result.content.strip())
