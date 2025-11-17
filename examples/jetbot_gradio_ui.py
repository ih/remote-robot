"""
Jetbot Remote Robot Control UI

A Gradio-based interface for controlling the Jetbot robot remotely.
Provides camera observation display and motor control capabilities.

Usage:
    python jetbot_gradio_ui.py

Make sure the Jetbot server is running before connecting.
"""

import gradio as gr
import numpy as np
import time
from typing import Optional, Dict, Any
from datetime import datetime

from remote_robot import JetbotRemote, JetbotConfig


# Global state
robot: Optional[JetbotRemote] = None
live_feed_active = False
last_auto_refresh_ts = 0.0


def connect_robot(host: str, port: int) -> tuple[str, str]:
    """Connect to the remote Jetbot server."""
    global robot

    try:
        if robot is not None and robot.is_connected:
            return "Already connected", "success"

        # Create config
        config = JetbotConfig()

        # Create remote robot instance
        robot = JetbotRemote(
            config=config,
            remote_host=host,
            remote_port=port
        )

        # Connect (no calibration needed for Jetbot)
        robot.connect()

        if robot.is_connected:
            return f"Connected to Jetbot at {host}:{port}", "success"
        else:
            return "Connection failed", "error"

    except Exception as e:
        robot = None
        return f"Error: {str(e)}", "error"


def disconnect_robot() -> tuple[str, str]:
    """Disconnect from the Jetbot robot."""
    global robot, live_feed_active, last_auto_refresh_ts

    try:
        if robot is None:
            return "Not connected", "warning"

        # Stop live feed if active
        live_feed_active = False
        last_auto_refresh_ts = 0.0

        robot.disconnect()
        robot = None
        return "Disconnected", "info"

    except Exception as e:
        return f"Error during disconnect: {str(e)}", "error"


def _prepare_image_for_display(image: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """Convert network BGR images into uint8 RGB arrays for Gradio."""
    if image is None:
        return None

    array = np.asarray(image)
    if array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)

    if array.ndim == 3 and array.shape[2] == 3:
        # Convert from OpenCV BGR to RGB for correct display colors
        array = array[:, :, ::-1]

    return array


def _extract_camera_image(obs: Dict[str, Any]) -> Optional[np.ndarray]:
    """Extract the best-guess camera frame from a robot observation."""
    for key in ("observation.images.main", "main", "camera"):
        if key in obs:
            return _prepare_image_for_display(obs[key])
    return None


def get_observation_once() -> tuple[Optional[np.ndarray], str, Dict[str, Any]]:
    """Get a single observation from the robot."""
    global robot

    if robot is None or not robot.is_connected:
        return None, "Not connected to robot", {}

    try:
        obs = robot.get_observation()
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        camera_image = _extract_camera_image(obs)

        # Extract motor values
        motor_feedback = {
            "left_motor.value": obs.get("left_motor.value", 0.0),
            "right_motor.value": obs.get("right_motor.value", 0.0),
        }

        status = f"Observation received at {timestamp}"
        return camera_image, status, motor_feedback

    except Exception as e:
        return None, f"Error: {str(e)}", {}


def send_action(left_motor: float, right_motor: float) -> tuple[str, Dict[str, Any]]:
    """Send motor commands to the robot and return updated motor feedback."""
    global robot

    if robot is None or not robot.is_connected:
        return "Not connected to robot", {}

    try:
        action = {
            "left_motor.value": left_motor,
            "right_motor.value": right_motor,
        }

        # DEBUG: Log the action being sent
        print(f"\n{'='*60}")
        print(f"[CLIENT] Sending action at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        print(f"[CLIENT] Action dict: {action}")
        print(f"[CLIENT] Robot connected: {robot.is_connected}")

        # Get observation BEFORE sending action
        obs_before = robot.get_observation()
        motor_values_before = {
            "left_motor.value": obs_before.get("left_motor.value", 0.0),
            "right_motor.value": obs_before.get("right_motor.value", 0.0),
        }
        print(f"[CLIENT] Motor values BEFORE action:")
        for key, val in motor_values_before.items():
            print(f"  {key}: {val:.3f}")

        # Send action
        result = robot.send_action(action)
        print(f"[CLIENT] send_action returned: {result}")
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Get updated observation after action
        time.sleep(0.1)  # Small delay for motors to respond
        obs = robot.get_observation()

        # Extract motor values
        motor_feedback = {
            "left_motor.value": obs.get("left_motor.value", 0.0),
            "right_motor.value": obs.get("right_motor.value", 0.0),
        }

        # Compare before and after
        print(f"[CLIENT] Motor values AFTER action:")
        for key, val in motor_feedback.items():
            before_val = motor_values_before.get(key, 0.0)
            delta = val - before_val
            print(f"  {key}: {val:.3f} (delta: {delta:+.3f})")
        print(f"{'='*60}\n")

        # Show the values being sent for debugging
        values_str = f"left: {left_motor:.2f}, right: {right_motor:.2f}"
        status = f"Action sent at {timestamp}\nValues: {values_str}\nCheck console for detailed debug info"

        return status, motor_feedback

    except Exception as e:
        print(f"[CLIENT] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", {}


def stop_motors() -> tuple[str, Dict[str, Any]]:
    """Emergency stop - set both motors to 0."""
    return send_action(0.0, 0.0)


# Create Gradio interface
with gr.Blocks(title="Jetbot Remote Control") as demo:
    gr.Markdown("# Jetbot Remote Robot Control Interface")
    gr.Markdown("Control the Jetbot differential drive robot and view camera observations.")

    with gr.Row():
        # Left column: Connection and Camera
        with gr.Column(scale=2):
            # Connection panel
            with gr.Group():
                gr.Markdown("### Connection")
                with gr.Row():
                    host_input = gr.Textbox(
                        label="Host",
                        value="192.168.68.51",
                        scale=2
                    )
                    port_input = gr.Number(
                        label="Port",
                        value=18861,
                        precision=0,
                        scale=1
                    )

                with gr.Row():
                    connect_btn = gr.Button("Connect", variant="primary")
                    disconnect_btn = gr.Button("Disconnect", variant="stop")

                connection_status = gr.Textbox(
                    label="Status",
                    value="Not connected",
                    interactive=False
                )

            # Camera display
            with gr.Group():
                gr.Markdown("### Camera Feed")
                camera_display = gr.Image(
                    label="Camera Observation",
                    type="numpy",
                    height=400
                )

                with gr.Row():
                    refresh_btn = gr.Button("Get Observation", variant="secondary")
                    live_feed_toggle = gr.Checkbox(
                        label="Auto-Refresh",
                        value=False
                    )
                refresh_interval_slider = gr.Slider(
                    minimum=0.25,
                    maximum=5.0,
                    value=1.0,
                    step=0.25,
                    label="Auto-Refresh Interval (seconds)"
                )

                observation_status = gr.Textbox(
                    label="Observation Status",
                    value="No observation yet",
                    interactive=False
                )

        # Right column: Motor Controls and Feedback
        with gr.Column(scale=1):
            # Motor controls
            with gr.Group():
                gr.Markdown("### Motor Controls")

                with gr.Row():
                    stop_btn = gr.Button("STOP", variant="stop", scale=2)

                action_status = gr.Textbox(
                    label="Action Status",
                    value="No action sent yet",
                    interactive=False
                )

            # Quick movement presets
            with gr.Group():
                gr.Markdown("### Quick Controls")
                with gr.Row():
                    forward_btn = gr.Button("Forward")
                    backward_btn = gr.Button("Backward")
                with gr.Row():
                    left_btn = gr.Button("Turn Left")
                    right_btn = gr.Button("Turn Right")

            # Observation feedback
            with gr.Group():
                gr.Markdown("### Robot Feedback")
                feedback_display = gr.JSON(
                    label="Motor Values",
                    value={}
                )

    # Event handlers
    def handle_connect(host, port):
        status, status_type = connect_robot(host, int(port))
        return status

    def handle_disconnect():
        status, _ = disconnect_robot()
        return status, gr.update(value=False)

    def handle_get_observation():
        image, status, feedback = get_observation_once()
        return [image, status, feedback]

    def handle_stop():
        return stop_motors()

    # Quick control handlers
    def handle_forward():
        return send_action(0.15, 0.15)

    def handle_backward():
        return send_action(-0.15, -0.15)

    def handle_turn_left():
        return send_action(-0.15, 0.15)

    def handle_turn_right():
        return send_action(0.15, -0.15)

    # Auto-refresh mechanism
    def handle_live_feed_toggle(enabled: bool):
        """Enable/disable live feed polling."""
        global live_feed_active, last_auto_refresh_ts

        if enabled and (robot is None or not robot.is_connected):
            live_feed_active = False
            return gr.update(value=False), "Connect to the robot before enabling auto-refresh"

        live_feed_active = bool(enabled)
        if enabled:
            last_auto_refresh_ts = 0.0

        message = "Auto-refresh enabled" if enabled else "Auto-refresh disabled"
        return gr.update(value=enabled), message

    def auto_refresh_feed(auto_refresh_enabled: bool, interval_seconds: float):
        """Called periodically when auto-refresh is enabled."""
        global last_auto_refresh_ts

        if not auto_refresh_enabled:
            return [gr.update(), gr.update(), gr.update()]

        wait_time = max(0.25, float(interval_seconds))
        now = time.time()
        if now - last_auto_refresh_ts < wait_time:
            return [gr.update(), gr.update(), gr.update()]

        last_auto_refresh_ts = now
        return handle_get_observation()

    # Connect events
    connect_btn.click(
        fn=handle_connect,
        inputs=[host_input, port_input],
        outputs=[connection_status]
    )

    disconnect_btn.click(
        fn=handle_disconnect,
        outputs=[connection_status, live_feed_toggle]
    )

    refresh_btn.click(
        fn=handle_get_observation,
        outputs=[camera_display, observation_status, feedback_display]
    )

    stop_btn.click(
        fn=handle_stop,
        outputs=[action_status, feedback_display]
    )

    # Quick control button events
    forward_btn.click(
        fn=handle_forward,
        outputs=[action_status, feedback_display]
    )

    backward_btn.click(
        fn=handle_backward,
        outputs=[action_status, feedback_display]
    )

    left_btn.click(
        fn=handle_turn_left,
        outputs=[action_status, feedback_display]
    )

    right_btn.click(
        fn=handle_turn_right,
        outputs=[action_status, feedback_display]
    )

    # Auto-refresh: Use a timer to periodically update when enabled
    live_feed_toggle.change(
        fn=handle_live_feed_toggle,
        inputs=[live_feed_toggle],
        outputs=[live_feed_toggle, observation_status]
    )

    # Create a timer that fires frequently; we throttle updates manually
    timer = gr.Timer(value=0.25)
    timer.tick(
        fn=auto_refresh_feed,
        inputs=[live_feed_toggle, refresh_interval_slider],
        outputs=[camera_display, observation_status, feedback_display]
    )


if __name__ == "__main__":
    print("Starting Jetbot Remote Control UI...")
    print("Default connection: localhost:18861")
    print("Note: For remote control, ensure the Jetbot server is running on the target device.")

    try:
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
    finally:
        # Cleanup on exit
        if robot is not None and robot.is_connected:
            disconnect_robot()
