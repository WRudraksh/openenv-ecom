# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""E-commerce Platform Manager Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import MyAction, MyObservation


class MyEnv(
    EnvClient[MyAction, MyObservation, State]
):
    """
    Client for the E-commerce Platform Manager Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.

    Example:
        >>> with MyEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.products)
        ...
        ...     action = MyAction(
        ...         pricing={"Laptop": "keep", "Headphones": "decrease"},
        ...         inventory={"Laptop": True},
        ...         marketing="run_ads"
        ...     )
        ...     result = client.step(action)
        ...     print(result.observation.profit)
    """

    def _step_payload(self, action: MyAction) -> Dict:
        """
        Convert MyAction to JSON payload for step message.

        Args:
            action: MyAction instance

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {
            "pricing": action.pricing,
            "inventory": action.inventory,
            "marketing": action.marketing,
        }

    def _parse_result(self, payload: Dict) -> StepResult[MyObservation]:
        """
        Parse server response into StepResult[MyObservation].

        Args:
            payload: JSON response data from server

        Returns:
            StepResult with MyObservation
        """
        obs_data = payload.get("observation", {})
        observation = MyObservation(
            products=obs_data.get("products", {}),
            customer_satisfaction=obs_data.get("customer_satisfaction", 1.0),
            marketing_active=obs_data.get("marketing_active", "none"),
            budget=obs_data.get("budget", 0.0),
            day=obs_data.get("day", 0),
            profit=obs_data.get("profit", 0.0),
            revenue=obs_data.get("revenue", 0.0),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from state request

        Returns:
            State object with episode_id and step_count
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
