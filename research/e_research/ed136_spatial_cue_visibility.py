"""Engineering-only MiniGrid visibility check on four previously exposed seeds."""
import json
import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

def run(seed):
    env = gym.make("MiniGrid-MemoryS13Random-v0")
    try:
        obs, _ = env.reset(seed=seed)
        frames = []
        for turn in range(5):
            array = obs["image"]
            positions = [
                [int(x), int(y), int(array[x, y, 0])]
                for x in range(7) for y in range(7)
                if int(array[x, y, 0]) in (OBJECT_TO_IDX["key"], OBJECT_TO_IDX["ball"])
            ]
            frames.append({"orientation": int(obs["direction"]), "positions": positions})
            if turn < 4:
                obs, reward, terminated, truncated, _ = env.step(0)
                assert not terminated and not truncated
        return {"seed": seed, "frames": frames}
    finally:
        env.close()

if __name__ == "__main__":
    assert minigrid.__version__ == "3.2.0"
    results = [run(seed) for seed in (84000, 84001, 84002, 84003)]
    assert results == [run(seed) for seed in (84000, 84001, 84002, 84003)]
    print(json.dumps({"status": "PASS_ENGINEERING_SPATIAL_OBSERVATION",
                      "scope": "EXPOSED_ENGINEERING_SEEDS_ONLY",
                      "not_ground_truth_cue": True, "results": results}))
