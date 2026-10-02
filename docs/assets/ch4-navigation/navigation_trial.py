"""Run one iGibson navigation trial and preserve incomplete runs for diagnosis."""
import json
import logging
import random
import sys
from pathlib import Path

seed = int(sys.argv[1])
policy = sys.argv[2]
if policy not in {"random", "goal"}:
    raise ValueError("policy must be random or goal")
out = Path("navigation-results") / f"seed-{seed}-{policy}"
out.mkdir(parents=True, exist_ok=False)
logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler(out / "run.log", mode="x", encoding="utf-8"),
    logging.StreamHandler(),
])
env, pending_action, metrics = None, None, None
positions, actions, rewards = [], [], []
result = dict(seed=seed, policy=policy, status="ERROR", completed=False,
              success=None, done=False, errors=[])

def failed(stage, error):
    result["errors"].append(dict(stage=stage, type=type(error).__name__, message=str(error)))
    logging.exception("Failed during %s", stage)

def require_finite(name, value):
    if not np.isfinite(np.asarray(value, dtype=np.float64)).all():
        raise ValueError(f"Non-finite {name}: {value!r}")

def save_rgb(name, state):
    pixels = (np.clip(state["rgb"], 0, 1) * 255).astype(np.uint8)
    Image.fromarray(pixels).save(out / name)

stage = "imports"
try:
    import igibson
    import numpy as np
    import yaml
    from PIL import Image
    from igibson.envs.igibson_env import iGibsonEnv

    random.seed(seed)
    np.random.seed(seed)
    stage = "configuration"
    config_path = Path(igibson.configs_path) / "turtlebot_interactive_nav.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config.update(enable_shadow=False, enable_pbr=False)
    (out / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    result.update(scene=config["scene_id"], task=config["task"])
    stage = "create_environment"
    env = iGibsonEnv(config_file=config, mode="gui_interactive", automatic_reset=False)
    stage = "reset"
    env.action_space.seed(seed)
    state = env.reset()  # This iGibson version returns only the observation.
    logging.info("observations: %s", {k: np.shape(v) for k, v in state.items()})
    logging.info("action space: %s", env.action_space)
    start = env.robots[0].get_position()[:2].copy()
    target = env.task.target_pos[:2].copy()
    require_finite("start", start)
    require_finite("target", target)
    shortest = float(env.task.geodesic_dist)
    require_finite("shortest_path_m", shortest)
    if not np.isfinite(shortest) or shortest <= 0:
        raise RuntimeError("Invalid initial shortest-path distance")
    positions.append(start.tolist())
    result.update(start=start.tolist(), target=target.tolist())
    stage = "start_image"
    save_rgb("start.png", state)
    done = False
    for step in range(config["max_step"]):
        stage = "action"
        if policy == "random":
            action = env.action_space.sample()
        else:
            bearing = float(state["task_obs"][1])
            require_finite("target bearing", bearing)
            action = np.array([0.2 if abs(bearing) < 0.25 else 0.0,
                               np.clip(bearing, -0.15, 0.15)], dtype=np.float32)
        require_finite("action", action)
        pending_action = dict(step=step + 1, action=action.tolist(), outcome="UNKNOWN")
        logging.info("Attempting action: %s", pending_action)
        stage = "step_or_observation"
        state, reward, done, info = env.step(action)
        pending_action.update(outcome="STEP_RETURNED", feedback_repr=dict(
            reward=repr(reward), done=repr(done), info=repr(info)))
        logging.info("Step returned: %s", pending_action)
        result["done"] = bool(done)
        stage = "step_feedback"
        reward = float(reward)
        require_finite("reward", reward)
        stage = "position_after_step"
        position = env.robots[0].get_position()[:2]
        pending_action["position_repr"] = repr(position)
        require_finite("position_after_step", position)
        positions.append(position.tolist())
        actions.append(action.tolist())
        rewards.append(reward)
        pending_action = None
        result["done"] = bool(done)
        logging.info("Confirmed step %s; reward=%s; done=%s", step + 1, reward, done)
        if done:
            break
    if not done:
        raise RuntimeError("Reached max_step without a terminal result")
    stage = "end_image"
    save_rgb("end.png", state)
    stage = "metrics"
    xy = np.asarray(positions)
    length = float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum())
    require_finite("path_length_m", length)
    require_finite("success", info["success"])
    require_finite("collision_step", info["collision_step"])
    success = bool(info["success"])
    metrics = dict(success=success, collision_steps=int(info["collision_step"]),
                   final_distance_m=float(np.linalg.norm(xy[-1] - target)),
                   shortest_path_m=shortest, path_length_m=length,
                   spl=float(success) * shortest / max(shortest, length))
    for name, value in metrics.items():
        require_finite(name, value)
except (Exception, KeyboardInterrupt) as error:
    failed(stage, error)
finally:
    if env is not None:
        try:
            env.close()
        except (Exception, KeyboardInterrupt) as error:
            failed("close", error)

if not result["errors"]:
    try:
        np.savez_compressed(out / "trajectory.npz", xy=np.asarray(positions),
                            actions=np.asarray(actions), rewards=np.asarray(rewards))
        result.update(metrics, status="COMPLETE", completed=True, trajectory_file="trajectory.npz")
    except Exception as error:
        failed("save_trajectory", error)
if result["errors"]:
    partial = dict(xy=positions, actions=actions, rewards=rewards,
                   unconfirmed_action=pending_action)
    try:
        (out / "trajectory_partial.json").write_text(
            json.dumps(partial, indent=2, allow_nan=False), encoding="utf-8")
        result["trajectory_file"] = "trajectory_partial.json"
    except Exception as error:
        failed("save_partial_trajectory", error)
result.update(steps=len(actions), unconfirmed_action=pending_action)
(out / "result.json").write_text(
    json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
logging.info("Final result: %s", result)
logging.shutdown()
sys.exit(0 if result["completed"] else 1)
