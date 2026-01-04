import random
from llm_backend.utils.logger import logger


class RewardTracker:
    """Simple database mock for tracking strategy rewards."""

    # storage: {strategy_name: [list_of_rewards]}
    _data = {
        "admin_priority": [0.8, 0.9, 0.7],
        "research_priority": [0.6, 0.7, 0.8],
        "balanced": [0.5, 0.6],
    }

    @classmethod
    def get_avg_reward(cls, strategy):
        rewards = cls._data.get(strategy, [])
        return sum(rewards) / len(rewards) if rewards else 0.5

    @classmethod
    def add_reward(cls, strategy, reward):
        if strategy not in cls._data:
            cls._data[strategy] = []
        cls._data[strategy].append(reward)
        logger.info(
            f"[RewardTracker] Strategy '{strategy}' updated with reward {reward}"
        )


class BanditHPTuner:
    """
    Advanced AutoRAG-HP: Uses a Multi-Armed Bandit (Epsilon-Greedy)
    to choose search strategies based on historical performance.
    """

    def __init__(self, epsilon=0.1):
        self.epsilon = epsilon
        # Strategies refined for KAIST CS / Internal domain
        self.strategies = {
            "kaist_admin": {
                "title_weight": 0.8,
                "dense_weight": 0.2,
                "sparse_weight": 0.1,
                "splade_weight": 0.1,
                "search_k": 40,
            },
            "kaist_research": {
                "title_weight": 0.1,
                "dense_weight": 0.4,
                "sparse_weight": 0.15,
                "splade_weight": 0.35,
                "search_k": 100,
            },
            "identity_lookup": {
                "title_weight": 0.7,
                "dense_weight": 0.2,
                "sparse_weight": 0.05,
                "splade_weight": 0.05,
                "search_k": 30,
            },
            "balanced": {
                "title_weight": 0.2,
                "dense_weight": 0.4,
                "sparse_weight": 0.2,
                "splade_weight": 0.2,
                "search_k": 60,
            },
        }

    def get_hp(self, query: str, context: str = "general"):
        """
        Selects the best strategy based on query context or historical reward.
        """
        # 1. Exploration (random)
        if random.random() < self.epsilon:
            strategy_name = random.choice(list(self.strategies.keys()))
            logger.info(f"[Bandit] EXPLORATION: Randomly chose '{strategy_name}'")
        else:
            # 2. Exploitation: Use avg rewards
            strategy_name = max(
                self.strategies.keys(), key=lambda s: RewardTracker.get_avg_reward(s)
            )
            logger.info(f"[Bandit) EXPLOITATION: Chose best strategy '{strategy_name}'")

        hp = self.strategies[strategy_name].copy()
        hp["_strategy_used"] = strategy_name
        return hp


# Usage in search_pipeline.py:
# tuner = BanditHPTuner()
# hp = tuner.get_hp(query)
# ... search ...
# ... user clicks like ... -> RewardTracker.add_reward(hp["_strategy_used"], 1.0)
