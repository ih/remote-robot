"""
SO-101 Remote Robot Control UI

A Gradio-based interface for controlling the SO-101 robot arm remotely.
Provides camera observation display and motor control capabilities.

Usage:
    python so101_gradio_ui.py

Make sure the SO-101 server is running before connecting.
"""

import gradio as gr
import numpy as np
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime

from remote_robot import SO101Remote
from lerobot.robots.so101_follower import SO101FollowerConfig


# Global state
robot: Optional[SO101Remote] = None
live_feed_active = False
live_feed_thread: Optional[threading.Thread] = None


def connect_robot(host: str, port: int) -> tuple[str, str]:
    """Connect to the SO-101 robot server."""
    global robot

    try:
        if robot is not None and robot.is_connected:
            return "Already connected", "success"

        # Create config (serial port doesn't matter for remote mode)
        config = SO101FollowerConfig(port="COM8")

        # Create remote robot instance
        robot = SO101Remote(
            config=config,
            remote_host=host,
            remote_port=port
        )

        # Connect without calibration
        robot.connect(calibrate=False)

        if robot.is_connected:
            return f"Connected to {host}:{port}", "success"
        else:
            return "Connection failed", "error"

    except Exception as e:
        robot = None
        return f"Error: {str(e)}", "error"


def disconnect_robot() -> tuple[str, str]:
    """Disconnect from the SO-101 robot server."""
    global robot, live_feed_active

    try:
        if robot is None:
            return "Not connected", "warning"

        # Stop live feed if active
        live_feed_active = False
        if live_feed_thread is not None:
            live_feed_thread.join(timeout=2.0)

        robot.disconnect()
        robot = None
        return "Disconnected", "info"

    except Exception as e:
        return f"Error during disconnect: {str(e)}", "error"


def calibrate_robot() -> str:
    """Calibrate the robot (must be connected first)."""
    global robot

    try:
        if robot is None or not robot.is_connected:
            return "Error: Must be connected first. Click 'Connect' before calibrating."

        # Call calibration on the robot
        robot.calibrate()
        return "Calibration completed successfully! Robot is ready to use."

    except Exception as e:
        return f"Calibration failed: {str(e)}"


def get_observation_once() -> tuple[Optional[np.ndarray], str, Dict[str, Any]]:
    """Get a single observation from the robot."""
    global robot

    if robot is None or not robot.is_connected:
        return None, "Not connected to robot", {}

    try:
        obs = robot.get_observation()
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Extract camera image if available
        camera_image = None
        if "observation.images.wrist" in obs:
            camera_image = obs["observation.images.wrist"]
        elif "main" in obs:
            camera_image = obs["main"]

        # Extract motor positions
        motor_feedback = {
            key: float(value) for key, value in obs.items()
            if not key.startswith("observation.images") and key != "main"
        }

        status = f"Observation received at {timestamp}"
        return camera_image, status, motor_feedback

    except Exception as e:
        return None, f"Error: {str(e)}", {}


def send_action(shoulder_pan: float, shoulder_lift: float, elbow_flex: float,
                wrist_flex: float, wrist_roll: float, gripper: float) -> tuple[str, Dict[str, Any]]:
    """Send motor commands to the robot and return updated motor feedback."""
    global robot

    if robot is None or not robot.is_connected:
        return "Not connected to robot", {}

    try:
        action = {
            "shoulder_pan.pos": shoulder_pan,
            "shoulder_lift.pos": shoulder_lift,
            "elbow_flex.pos": elbow_flex,
            "wrist_flex.pos": wrist_flex,
            "wrist_roll.pos": wrist_roll,
            "gripper.pos": gripper,
        }

        # CLIENT DEBUG: Log the action being sent
        print(f"\n{'='*60}")
        print(f"[CLIENT] Sending action at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        print(f"[CLIENT] Action dict: {action}")
        print(f"[CLIENT] Robot connected: {robot.is_connected}")
        print(f"[CLIENT] Robot calibrated: {robot.is_calibrated}")

        # Get observation BEFORE sending action
        obs_before = robot.get_observation()
        motor_positions_before = {
            key: float(value) for key, value in obs_before.items()
            if not key.startswith("observation.images") and key != "main"
        }
        print(f"[CLIENT] Motor positions BEFORE action:")
        for key, val in motor_positions_before.items():
            print(f"  {key}: {val:.3f}")

        # Send action
        result = robot.send_action(action)
        print(f"[CLIENT] send_action returned: {result}")
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Get updated observation after action
        time.sleep(0.1)  # Small delay for motors to start moving
        obs = robot.get_observation()

        # Extract motor positions
        motor_feedback = {
            key: float(value) for key, value in obs.items()
            if not key.startswith("observation.images") and key != "main"
        }

        # Compare before and after
        print(f"[CLIENT] Motor positions AFTER action:")
        for key, val in motor_feedback.items():
            before_val = motor_positions_before.get(key, 0.0)
            delta = val - before_val
            print(f"  {key}: {val:.3f} (delta: {delta:+.3f})")
        print(f"{'='*60}\n")

        # Show the values being sent for debugging
        values_str = ", ".join([f"{k.split('.')[0]}: {v:.2f}" for k, v in action.items()])
        status = f"Action sent at {timestamp}\nValues: {values_str}\nCheck console for detailed debug info"

        return status, motor_feedback

    except Exception as e:
        print(f"[CLIENT] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", {}


def live_feed_worker(interval: float):
    """Background worker for live camera feed."""
    global live_feed_active

    while live_feed_active:
        time.sleep(interval)


def toggle_live_feed(active: bool, interval: float) -> str:
    """Start or stop the live camera feed."""
    global live_feed_active, live_feed_thread

    if active:
        if robot is None or not robot.is_connected:
            return "Cannot start live feed: Not connected"

        live_feed_active = True
        live_feed_thread = threading.Thread(
            target=live_feed_worker,
            args=(interval,),
            daemon=True
        )
        live_feed_thread.start()
        return "Live feed started"
    else:
        live_feed_active = False
        if live_feed_thread is not None:
            live_feed_thread.join(timeout=2.0)
        return "Live feed stopped"


def update_live_feed():
    """Update function for live feed (called by Gradio)."""
    if not live_feed_active or robot is None or not robot.is_connected:
        return None

    try:
        obs = robot.get_observation()

        # Extract camera image
        if "observation.images.wrist" in obs:
            return obs["observation.images.wrist"]
        elif "main" in obs:
            return obs["main"]
        return None

    except Exception:
        return None


# Create Gradio interface
with gr.Blocks(title="SO-101 Remote Control") as demo:
    gr.Markdown("# SO-101 Remote Robot Control Interface")
    gr.Markdown("Control the SO-101 robot arm and view camera observations remotely.")

    with gr.Row():
        # Left column: Connection and Camera
        with gr.Column(scale=2):
            # Connection panel
            with gr.Group():
                gr.Markdown("### Connection")
                with gr.Row():
                    host_input = gr.Textbox(
                        label="Host",
                        value="localhost",
                        scale=2
                    )
                    port_input = gr.Number(
                        label="Port",
                        value=18862,
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

                calibrate_btn = gr.Button("Calibrate Robot", variant="secondary")
                calibration_status = gr.Textbox(
                    label="Calibration Status",
                    value="Not calibrated yet",
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
                    live_feed_checkbox = gr.Checkbox(
                        label="Live Feed",
                        value=False
                    )
                    live_feed_interval = gr.Slider(
                        label="Update Interval (s)",
                        minimum=0.1,
                        maximum=2.0,
                        value=0.2,
                        step=0.1
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

                motor_controls = []
                motor_names = [
                    ("shoulder_pan", "Shoulder Pan (deg)", -180.0, 180.0, 0.0),
                    ("shoulder_lift", "Shoulder Lift (deg)", -180.0, 180.0, 0.0),
                    ("elbow_flex", "Elbow Flex (deg)", -180.0, 180.0, 0.0),
                    ("wrist_flex", "Wrist Flex (deg)", -180.0, 180.0, 0.0),
                    ("wrist_roll", "Wrist Roll (deg)", -180.0, 180.0, 0.0),
                    ("gripper", "Gripper (%)", 0.0, 100.0, 0.0),
                ]

                for key, label, min_val, max_val, default in motor_names:
                    with gr.Row():
                        slider = gr.Slider(
                            label=label,
                            minimum=min_val,
                            maximum=max_val,
                            value=default,
                            step=0.01,
                            scale=3
                        )
                        number = gr.Number(
                            value=default,
                            precision=3,
                            scale=1
                        )

                    # Synchronize slider and number input
                    slider.change(fn=lambda x: x, inputs=[slider], outputs=[number])
                    number.change(fn=lambda x: x, inputs=[number], outputs=[slider])

                    motor_controls.append((slider, number))

                send_action_btn = gr.Button("Send Action", variant="primary")
                action_status = gr.Textbox(
                    label="Action Status",
                    value="No action sent yet",
                    interactive=False
                )

            # Observation feedback
            with gr.Group():
                gr.Markdown("### Robot Feedback")
                feedback_display = gr.JSON(
                    label="Motor Positions",
                    value={}
                )

    # Event handlers
    def handle_connect(host, port):
        status, status_type = connect_robot(host, int(port))
        return status

    def handle_disconnect():
        status, status_type = disconnect_robot()
        return status

    def handle_calibrate():
        status = calibrate_robot()
        return status

    def handle_get_observation():
        image, status, feedback = get_observation_once()
        # Extract motor positions for sliders
        positions = [
            feedback.get("shoulder_pan.pos", 0.0),
            feedback.get("shoulder_lift.pos", 0.0),
            feedback.get("elbow_flex.pos", 0.0),
            feedback.get("wrist_flex.pos", 0.0),
            feedback.get("wrist_roll.pos", 0.0),
            feedback.get("gripper.pos", 0.0),
        ]
        return [image, status, feedback] + positions

    def handle_send_action(*motor_values):
        # motor_values already contains the 6 slider values
        status, feedback = send_action(*motor_values)
        # Extract motor positions for sliders
        positions = [
            feedback.get("shoulder_pan.pos", 0.0),
            feedback.get("shoulder_lift.pos", 0.0),
            feedback.get("elbow_flex.pos", 0.0),
            feedback.get("wrist_flex.pos", 0.0),
            feedback.get("wrist_roll.pos", 0.0),
            feedback.get("gripper.pos", 0.0),
        ]
        return [status] + positions

    def handle_live_feed_toggle(active, interval):
        status = toggle_live_feed(active, interval)
        return status

    # Connect events
    connect_btn.click(
        fn=handle_connect,
        inputs=[host_input, port_input],
        outputs=[connection_status]
    )

    disconnect_btn.click(
        fn=handle_disconnect,
        outputs=[connection_status]
    )

    calibrate_btn.click(
        fn=handle_calibrate,
        outputs=[calibration_status]
    )

    # Get all sliders for inputs/outputs
    sliders = [slider for slider, _ in motor_controls]

    refresh_btn.click(
        fn=handle_get_observation,
        outputs=[camera_display, observation_status, feedback_display] + sliders
    )

    send_action_btn.click(
        fn=handle_send_action,
        inputs=sliders,
        outputs=[action_status] + sliders
    )

    # Live feed toggle
    live_feed_checkbox.change(
        fn=handle_live_feed_toggle,
        inputs=[live_feed_checkbox, live_feed_interval],
        outputs=[observation_status]
    )

    # Note: Auto-update with 'every' parameter is not supported in Gradio 5.x
    # Users can manually refresh or use the live feed toggle with manual polling


if __name__ == "__main__":
    print("Starting SO-101 Remote Control UI...")
    print("Make sure the SO-101 server is running before connecting.")
    print("Default connection: localhost:18862")

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
