# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the E-commerce Platform Manager Environment.

The environment simulates an e-commerce platform where an agent must
maximize profit while maintaining customer satisfaction.
"""

from typing import Dict, Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class ProductState(Observation):
    """State of a single product."""

    price: float = Field(default=0.0, description="Current selling price")
    cost: float = Field(default=0.0, description="Cost to purchase/produce")
    stock: int = Field(default=0, description="Current stock level")
    demand: int = Field(default=0, description="Current demand level")
    competitor_price: float = Field(default=0.0, description="Competitor's price for this product")


class MyObservation(Observation):
    """Observation from the E-commerce Platform Manager environment."""

    products: Dict[str, Dict] = Field(default_factory=dict, description="Product states keyed by product name")
    customer_satisfaction: float = Field(default=1.0, description="Customer satisfaction score (0-1)")
    marketing_active: str = Field(default="none", description="Currently active marketing campaign")
    budget: float = Field(default=0.0, description="Available budget")
    day: int = Field(default=0, description="Current simulation day")
    profit: float = Field(default=0.0, description="Profit from the last step")
    revenue: float = Field(default=0.0, description="Revenue from the last step")


class MyAction(Action):
    """Action for the E-commerce Platform Manager environment."""

    pricing: Dict[str, Literal["increase", "decrease", "keep"]] = Field(
        default_factory=dict,
        description="Pricing decisions per product: increase / decrease / keep"
    )
    inventory: Dict[str, bool] = Field(
        default_factory=dict,
        description="Restock decisions per product: True to restock, False to skip"
    )
    marketing: Literal["run_ads", "influencer", "no_campaign"] = Field(
        default="no_campaign",
        description="Marketing campaign choice: run_ads / influencer / no_campaign"
    )
