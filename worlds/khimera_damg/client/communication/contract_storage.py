from collections.abc import Callable
from functools import partial

from .agents import AgentV1
from .classes import CommunicationAgent, CommunicationContract
from .contracts import ContractV1

component_list: dict[tuple[int, int, int], tuple[type[CommunicationContract], type[CommunicationAgent]]] = {
    (0, 0, 0): (ContractV1, AgentV1)
}


def get_agent(contract_version: str) -> Callable[[], CommunicationAgent]:
    digits = tuple(map(int, contract_version.split(".")))
    if len(digits) != 3:
        raise ValueError("Version strings must be composed of 3 numbers separated by dots.")
    # This function is barely ever called and the lookup dictionary will never be big enough.
    # It's ok for this to stay suboptimal.

    key: tuple[int, int, int] | None = max((k for k in component_list if k <= digits), default=None)
    if key is None:
        raise ValueError("Couldn't find a contract that matches this version. "
                         "(Please don't use negative values in versions)")
    contract, agent = component_list[key]

    return partial(agent, contract)
