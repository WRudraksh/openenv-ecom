from server.my_env_environment import MyEnvironment
from models import MyAction

def make_env():
    env = MyEnvironment()
    env.reset()
    return env

def test_reset_initializes_state():
    env = make_env()
    obs = env.reset()
    assert obs.day == 0
    assert obs.budget == 10000.0
    assert obs.customer_satisfaction == 1.0
    assert len(obs.products) == 5

def test_step_increments_day():
    env = make_env()
    action = MyAction(pricing={}, inventory={}, marketing="no_campaign")
    obs = env.step(action)
    assert obs.day == 1

def test_budget_cannot_go_below_zero_from_restocking():
    env = make_env()
    env._budget = 100.0  # barely any budget
    action = MyAction(
        pricing={},
        inventory={name: True for name in env._products},
        marketing="no_campaign"
    )
    obs = env.step(action)
    assert obs.budget >= 0  # may be near zero but not negative

def test_stockout_detected_correctly():
    env = make_env()
    for prod in env._products.values():
        prod["stock"] = 0   # force zero stock
        prod["demand"] = 10
    action = MyAction(pricing={}, inventory={}, marketing="no_campaign")
    # Should record stockouts (all products have demand > stock)
    # Check satisfaction drops
    prev_sat = env._customer_satisfaction
    env.step(action)
    assert env._customer_satisfaction < prev_sat

def test_demand_does_not_accumulate_from_ads():
    env = make_env()
    initial_demands = {k: v["base_demand"] for k, v in env._products.items()}
    for _ in range(5):
        action = MyAction(pricing={}, inventory={}, marketing="run_ads")
        env.step(action)
    # Demand should not be 5x boosted — ads should be single-step only
    for name, prod in env._products.items():
        assert prod["demand"] <= initial_demands[name] * 2  # rough sanity bound

def test_episode_ends_at_day_30():
    env = make_env()
    action = MyAction(pricing={}, inventory={}, marketing="no_campaign")
    obs = None
    for _ in range(30):
        obs = env.step(action)
    assert obs.done == True

def test_lower_price_increases_demand_modifier():
    env = make_env()
    prod_name = "Laptop"
    initial_modifier = env._products[prod_name]["demand_modifier"]
    action = MyAction(
        pricing={prod_name: "decrease"},
        inventory={},
        marketing="no_campaign"
    )
    env.step(action)
    assert env._products[prod_name]["demand_modifier"] > initial_modifier
