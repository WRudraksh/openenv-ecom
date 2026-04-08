# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
E-commerce Platform Manager Environment Implementation.

Simulates an e-commerce platform where an agent must maximize profit
while maintaining customer satisfaction through pricing, inventory,
and marketing decisions.
"""

from uuid import uuid4
import math
import numpy as np

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import MyAction, MyObservation
except ImportError:
    from models import MyAction, MyObservation


# Default product catalog
DEFAULT_PRODUCTS = {
    "Laptop": {
        "price": 999.0,
        "cost": 600.0,
        "stock": 50,
        "demand": 30,
        "competitor_price": 950.0,
    },
    "Headphones": {
        "price": 149.0,
        "cost": 50.0,
        "stock": 200,
        "demand": 120,
        "competitor_price": 139.0,
    },
    "Smartphone": {
        "price": 699.0,
        "cost": 400.0,
        "stock": 80,
        "demand": 60,
        "competitor_price": 679.0,
    },
    "Tablet": {
        "price": 449.0,
        "cost": 250.0,
        "stock": 60,
        "demand": 40,
        "competitor_price": 429.0,
    },
    "Smartwatch": {
        "price": 249.0,
        "cost": 100.0,
        "stock": 100,
        "demand": 70,
        "competitor_price": 239.0,
    },
}

RESTOCK_AMOUNT = 30
RESTOCK_COST_MULTIPLIER = 1.0  # cost per unit for restocking = product cost * multiplier
ADS_COST = 200.0
INFLUENCER_COST = 350.0
ADS_DEMAND_BOOST = 10  # flat demand increase per product
INFLUENCER_SATISFACTION_BOOST = 0.05
PRICE_CHANGE_AMOUNT = 20.0  # flat amount prices change by
DEMAND_CHANGE_ON_PRICE = 5  # demand change when price changes


class MyEnvironment(Environment):
    """
    E-commerce Platform Manager environment.

    The agent manages an e-commerce platform by making decisions on:
    1. Pricing: increase / decrease / keep per product
    2. Inventory: restock True/False per product
    3. Marketing: run_ads / influencer / no_campaign

    The goal is to maximize profit while maintaining customer satisfaction.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        """Initialize the e-commerce environment."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._products = {}
        self._customer_satisfaction = 1.0
        self._marketing_active = "none"
        self._budget = 10000.0
        self._day = 0
        self._last_profit = 0.0
        self._last_revenue = 0.0
        self._rng = np.random.default_rng(seed=42)
        self._seasonal_factor = 1.0

    def _init_products(self):
        """Initialize product catalog with default values."""
        self._products = {}
        for name, data in DEFAULT_PRODUCTS.items():
            self._products[name] = {
                "price": data["price"],
                "cost": data["cost"],
                "stock": data["stock"],
                "demand": data["demand"],
                "competitor_price": data["competitor_price"],
                "base_demand": data["demand"],
                "demand_modifier": 0,
                "profit_last_step": 0.0,
                "stockout": False,
            }

    def _build_observation(self, reward: float = 0.0, done: bool = False) -> MyObservation:
        """Build an observation from current internal state."""
        products_dict = {}
        for name, data in self._products.items():
            products_dict[name] = {
                "price": data["price"],
                "cost": data["cost"],
                "stock": data["stock"],
                "demand": data["demand"],
                "competitor_price": data["competitor_price"],
                "profit_last_step": data.get("profit_last_step", 0.0),
                "stockout": data.get("stockout", False),
            }

        return MyObservation(
            products=products_dict,
            customer_satisfaction=round(self._customer_satisfaction, 4),
            marketing_active=self._marketing_active,
            budget=round(self._budget, 2),
            day=self._day,
            profit=round(self._last_profit, 2),
            revenue=round(self._last_revenue, 2),
            seasonal_factor=round(getattr(self, "_seasonal_factor", 1.0), 4),
            day_of_week=self._day % 7,
            done=done,
            reward=round(reward, 4),
        )

    def reset(self) -> MyObservation:
        """
        Reset the environment to initial state.

        Returns:
            MyObservation with the initial product catalog and metrics.
        """
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._init_products()
        self._customer_satisfaction = 1.0
        self._marketing_active = "none"
        self._budget = 10000.0
        self._day = 0
        self._last_profit = 0.0
        self._last_revenue = 0.0
        self._rng = np.random.default_rng(seed=42)
        self._seasonal_factor = 1.0

        return self._build_observation(reward=0.0, done=False)

    def step(self, action: MyAction) -> MyObservation:  # type: ignore[override]
        """
        Execute one step in the e-commerce simulation.

        Args:
            action: MyAction with pricing, inventory, and marketing decisions.

        Returns:
            MyObservation with updated state, reward, and metrics.
        """
        self._state.step_count += 1
        self._day += 1

        self._seasonal_factor = 1.0 + 0.2 * math.sin(2 * math.pi * self._day / 7)

        # Pre-step: Reset demand and apply noise/seasonality
        for prod in self._products.values():
            prod["demand"] = max(0, prod["base_demand"] + prod["demand_modifier"])
            prod["demand"] = max(0, int(prod["demand"] * self._seasonal_factor))
            noise = self._rng.normal(0, max(2, prod["demand"] * 0.1))
            prod["demand"] = max(0, int(prod["demand"] + noise))
            prod["stockout"] = False

        # ── 1. Pricing Update ──────────────────────────────────────────
        PRICE_ELASTICITY = 0.08
        for product_name, decision in action.pricing.items():
            if product_name not in self._products:
                continue
            prod = self._products[product_name]
            if decision == "increase":
                prod["price"] = round(prod["price"] + PRICE_CHANGE_AMOUNT, 2)
                delta = int(prod["base_demand"] * PRICE_ELASTICITY)
                prod["demand_modifier"] = max(-50, prod["demand_modifier"] - delta)
            elif decision == "decrease":
                prod["price"] = round(max(prod["cost"] * 1.05, prod["price"] - PRICE_CHANGE_AMOUNT), 2)
                delta = int(prod["base_demand"] * PRICE_ELASTICITY)
                prod["demand_modifier"] = min(50, prod["demand_modifier"] + delta)

        # ── 2. Inventory (Restocking) ──────────────────────────────────
        restock_total_cost = 0.0
        for product_name, should_restock in action.inventory.items():
            if product_name not in self._products:
                continue
            if should_restock:
                prod = self._products[product_name]
                cost = prod["cost"] * RESTOCK_COST_MULTIPLIER * RESTOCK_AMOUNT
                if self._budget >= cost:
                    prod["stock"] += RESTOCK_AMOUNT
                    self._budget -= cost
                    restock_total_cost += cost

        # ── 3. Marketing ──────────────────────────────────────────────
        self._marketing_active = "none"
        if action.marketing == "run_ads":
            if self._budget >= ADS_COST:
                self._budget -= ADS_COST
                self._marketing_active = "ads"
                # Demand boost across all products
                for prod in self._products.values():
                    prod["demand"] += ADS_DEMAND_BOOST
        elif action.marketing == "influencer":
            if self._budget >= INFLUENCER_COST:
                self._budget -= INFLUENCER_COST
                self._marketing_active = "influencer"
                # Satisfaction boost
                self._customer_satisfaction = min(1.0, self._customer_satisfaction + INFLUENCER_SATISFACTION_BOOST)

        # ── 4. Sales Simulation ────────────────────────────────────────
        total_revenue = 0.0
        total_cost_of_goods = 0.0
        total_stockouts = 0
        overpriced_count = 0

        for product_name, prod in self._products.items():
            # Track stockouts (demand exceeded stock)
            if prod["demand"] > prod["stock"]:
                total_stockouts += 1
                prod["stockout"] = True

            sales = min(prod["stock"], prod["demand"])
            revenue = sales * prod["price"]
            cogs = sales * prod["cost"]

            prod["profit_last_step"] = revenue - cogs

            total_revenue += revenue
            total_cost_of_goods += cogs

            prod["stock"] -= sales

            # Track overpriced products
            if prod["price"] > prod["competitor_price"] * 1.15:
                overpriced_count += 1

        total_profit = total_revenue - total_cost_of_goods

        HOLDING_COST_PER_UNIT = 0.5
        holding_cost = sum(p["stock"] for p in self._products.values()) * HOLDING_COST_PER_UNIT
        self._budget -= holding_cost
        total_profit -= holding_cost

        self._budget += total_profit

        self._last_revenue = total_revenue
        self._last_profit = total_profit

        # ── 4.5 Competitor Price Drift ─────────────────────────────────
        for prod in self._products.values():
            drift = self._rng.uniform(-5, 5)
            prod["competitor_price"] = round(max(prod["cost"] * 1.1, prod["competitor_price"] + drift), 2)

        # ── 5. Satisfaction Update ─────────────────────────────────────
        # Penalize stockouts
        stockout_penalty = total_stockouts * 0.05
        self._customer_satisfaction -= stockout_penalty

        # Penalize overpriced products
        overprice_penalty = overpriced_count * 0.03
        self._customer_satisfaction -= overprice_penalty

        # Reward good marketing
        if self._marketing_active == "ads":
            self._customer_satisfaction += 0.02
        elif self._marketing_active == "influencer":
            # Already boosted above, small extra
            self._customer_satisfaction += 0.01

        # Clamp satisfaction to [0, 1]
        self._customer_satisfaction = max(0.0, min(1.0, self._customer_satisfaction))

        # ── 6. Reward Calculation ──────────────────────────────────────
        max_possible_revenue = sum(
            p["base_demand"] * p["price"] for p in self._products.values()
        )
        normalized_profit = total_profit / max(max_possible_revenue, 1)

        stockout_rate = total_stockouts / len(self._products)
        budget_health = max(0, self._budget / 10000.0)

        reward = (
            normalized_profit * 100.0
            + self._customer_satisfaction * 20.0
            - stockout_rate * 30.0
            + budget_health * 10.0
        )

        # End after 30 days
        done = self._day >= 30

        return self._build_observation(reward=reward, done=done)

    @property
    def state(self) -> State:
        """
        Get the current environment state.

        Returns:
            Current State with episode_id and step_count.
        """
        return self._state
