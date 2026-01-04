from llm_backend.vectorstore.bandit_tuner import RewardTracker
from llm_backend.utils.logger import logger


def log_search_feedback(strategy_name: str, feedback_type: str):
    """
    Mock API endpoint to collect user feedback.

    Args:
        strategy_name: The strategy identified by '_strategy_used' in the result.
        feedback_type: 'like', 'dislike', 'copy', etc.
    """
    # 1. Map feedback type to numeric reward
    mapping = {
        "like": 1.0,
        "dislike": -1.0,
        "copy": 0.5,
        "stay": 0.2,  # Implicit: user stayed on result
    }

    reward = mapping.get(feedback_type, 0.0)

    # 2. Update the RewardTracker (Online Learning)
    RewardTracker.add_reward(strategy_name, reward)

    logger.info(
        f"[FeedbackAPI] Success: Strategy '{strategy_name}' received reward {reward} via '{feedback_type}'"
    )
    return {"status": "success", "strategy": strategy_name, "reward": reward}


if __name__ == "__main__":
    # Simulated Feedback Loop
    print("=== Simulating User Feedback Loop ===")

    # User likes an administrative result (kaist_admin strategy)
    res = log_search_feedback("kaist_admin", "like")
    print(f"Feedback Logged: {res}")

    # User dislikes a research result (balanced strategy)
    res = log_search_feedback("balanced", "dislike")
    print(f"Feedback Logged: {res}")

    # Check updated averages
    print(
        f"\nNew Avg Reward (kaist_admin): {RewardTracker.get_avg_reward('kaist_admin')}"
    )
    print(f"New Avg Reward (balanced): {RewardTracker.get_avg_reward('balanced')}")
