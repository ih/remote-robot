# remote-robot

**LeRobot 0.4.1+ compatible remote robot control for Jetbot and SO-101**

A Python package providing unified, LeRobot-compatible interfaces for remotely controlling Jetbot and SO-101 robots via RPyC. Supports both local and remote operation with drop-in API compatibility.

## Features

- **LeRobot API Compatible**: Fully compatible with LeRobot 0.4.1+ `Robot` base class
- **Remote Control**: RPyC-based client-server architecture for network robot control
- **Drop-in Replacement**: `SO101Remote` can replace `SO101Follower` in existing code
- **Unified Interface**: Both robots implement the same LeRobot patterns
- **Easy Integration**: Works with LeRobot's dataset collection and teleoperation tools
- **Mock Support**: Test code without physical hardware

## Supported Robots

- **Jetbot**: Differential drive mobile robot (Waveshare JetBot AI Kit)
- **SO-101**: 6-DOF robot arm (SO-101 Follower from LeRobot)

## Installation

### Basic Installation

```bash
# Clone the repository
cd remote-robot

# Install package
pip install -e .
```

### With Optional Dependencies

```bash
# For Jetbot hardware support
pip install -e .[jetbot]

# For development
pip install -e .[dev]
```

## Quick Start

### Local Control (Jetbot)

```python
from remote_robot import Jetbot, JetbotConfig

# Configure robot
config = JetbotConfig(mock=False)  # Set mock=True for testing
robot = Jetbot(config)

# Connect and control
robot.connect()
robot.send_action({"left_motor.value": 0.5, "right_motor.value": 0.5})
obs = robot.get_observation()
robot.disconnect()
```

### Remote Control (SO-101)

**On SO-101 machine (server):**
```bash
# Windows
python examples/run_so101_server.py --port COM8

# Linux/macOS
python examples/run_so101_server.py --port /dev/ttyUSB0
```

**On control machine (client):**
```python
from remote_robot import SO101Remote
from lerobot.robots.so101_follower import SO101FollowerConfig

config = SO101FollowerConfig(port="COM8")  # Use /dev/ttyUSB0 on Linux/macOS
robot = SO101Remote(config, remote_host="192.168.1.100")

robot.connect()
action = {"shoulder_pan.pos": 0.0, "gripper.pos": 0.5}
robot.send_action(action)
robot.disconnect()
```

## Architecture

### Package Structure

```
remote-robot/
├── src/remote_robot/
│   ├── robots/              # Robot implementations
│   │   ├── jetbot.py        # Jetbot robot class
│   │   ├── jetbot_config.py # Jetbot configuration
│   │   └── so101_remote.py  # SO-101 remote wrapper
│   ├── server/              # RPyC servers
│   │   ├── base.py          # Base server class
│   │   ├── jetbot_server.py # Jetbot server
│   │   └── so101_server.py  # SO-101 server
│   └── utils/               # Utilities
│       ├── serialization.py # Data encoding/decoding
│       └── remote_client.py # RPyC connection helpers
└── examples/                # Example scripts
```

### Robot Classes

#### Jetbot

Uses the official `jetbot` package for hardware control.

**Action Features:**
- `left_motor.value`: Left motor speed [-1, 1]
- `right_motor.value`: Right motor speed [-1, 1]

**Observation Features:**
- `left_motor.value`: Current left motor speed
- `right_motor.value`: Current right motor speed
- Camera images (if configured)

#### SO101Remote

Wraps LeRobot's `SO101Follower` with optional remote control.

**Action Features:**
- `shoulder_pan.pos`: Shoulder pan position
- `shoulder_lift.pos`: Shoulder lift position
- `elbow_flex.pos`: Elbow flex position
- `wrist_flex.pos`: Wrist flex position
- `wrist_roll.pos`: Wrist roll position
- `gripper.pos`: Gripper position

**Observation Features:**
- Same as action features (motor positions)
- Camera images (if configured)

## Deployment

### Deploying Jetbot Server to Jetson Nano

The Jetbot server has **minimal dependencies** and does NOT require LeRobot installation on the Jetson Nano.

**On Jetson Nano:**
```bash
# Install dependencies only (no need to install full package)
pip3 install rpyc opencv-python numpy

# Copy server file to Jetbot
# Option 1: Copy entire src/remote_robot/server directory
# Option 2: Just copy jetbot_server.py (it's standalone)

# Run the server
python3 jetbot_server.py
```

The server only needs: `rpyc`, `jetbot`, `opencv-python`, `numpy` - all compatible with Jetson Nano!

## Usage Examples

### 1. Running Servers

**Jetbot Server (on Jetbot hardware):**
```bash
# Using the standalone server file
cd src/remote_robot/server
python3 jetbot_server.py

# Or using the example script
python3 examples/run_jetbot_server.py
```

**SO-101 Server (on machine with SO-101):**
```bash
python examples/run_so101_server.py --port /dev/ttyUSB0
```

### 2. Local Control

See `examples/jetbot_local_control.py`:

```python
from remote_robot import Jetbot, JetbotConfig

config = JetbotConfig(mock=True)
robot = Jetbot(config)
robot.connect()

# Drive forward
robot.send_action({"left_motor.value": 0.3, "right_motor.value": 0.3})

# Get observation
obs = robot.get_observation()
print(obs)

robot.disconnect()
```

### 3. Remote Control

See `examples/so101_remote_control.py`:

```python
from remote_robot import SO101Remote
from lerobot.robots.so101_follower import SO101FollowerConfig

config = SO101FollowerConfig(port="/dev/ttyUSB0")
robot = SO101Remote(config, remote_host="192.168.1.100", remote_port=18862)

robot.connect()
# Control robot...
robot.disconnect()
```

### 4. Integration with LeRobot

```python
from lerobot.common.datasets import record_episode
from remote_robot import Jetbot, JetbotConfig

config = JetbotConfig(mock=False)
robot = Jetbot(config)

# Use with LeRobot's recording tools
record_episode(robot=robot, ...)
```

## Configuration

### JetbotConfig

```python
@dataclass
class JetbotConfig(RobotConfig):
    mock: bool = False  # Use mock hardware for testing
    disable_motors_on_disconnect: bool = True
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
```

### SO101FollowerConfig

Uses LeRobot's standard `SO101FollowerConfig`. See [LeRobot documentation](https://github.com/huggingface/lerobot) for details.

## Network Configuration

### Default Ports

- **Jetbot**: 18861
- **SO-101**: 18862

### Firewall Setup

Ensure ports are open on server machines:

```bash
# Ubuntu/Debian
sudo ufw allow 18861/tcp  # Jetbot
sudo ufw allow 18862/tcp  # SO-101

# Check status
sudo ufw status
```

## Development

### Running Tests

```bash
pip install -e .[dev]
pytest tests/
```

### Code Formatting

```bash
black src/ examples/
isort src/ examples/
```

## API Reference

### Jetbot

```python
class Jetbot(Robot):
    """LeRobot-compatible Jetbot robot."""

    def __init__(self, config: JetbotConfig)
    def connect(self, calibrate: bool = True) -> None
    def disconnect(self) -> None
    def get_observation(self) -> dict[str, Any]
    def send_action(self, action: dict[str, Any]) -> dict[str, Any]

    @property
    def is_connected(self) -> bool
    @property
    def is_calibrated(self) -> bool
    @property
    def observation_features(self) -> dict
    @property
    def action_features(self) -> dict
```

### SO101Remote

```python
class SO101Remote(Robot):
    """LeRobot-compatible SO-101 with remote control."""

    def __init__(
        self,
        config: SO101FollowerConfig,
        remote_host: Optional[str] = None,
        remote_port: int = 18862
    )

    # Same methods as Jetbot...
```

## Troubleshooting

### Connection Issues

1. **Check network connectivity:**
   ```bash
   ping <robot-ip>
   ```

2. **Verify server is running:**
   ```bash
   netstat -an | grep 18861  # For Jetbot
   netstat -an | grep 18862  # For SO-101
   ```

3. **Check firewall settings** (see Network Configuration above)

### Hardware Issues

1. **Jetbot not responding:**
   - Verify `jetbot` package is installed: `pip show jetbot`
   - Check I2C connection: `i2cdetect -y 1`
   - Verify motor controller address (usually 0x60)

2. **SO-101 connection errors:**
   - Check serial port: `ls /dev/ttyUSB*`
   - Verify permissions: `sudo chmod 666 /dev/ttyUSB0`
   - Test with LeRobot directly first

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on [LeRobot](https://github.com/huggingface/lerobot) by Hugging Face
- Uses [RPyC](https://rpyc.readthedocs.io/) for remote procedure calls
- Jetbot support based on the [jetbot](https://github.com/NVIDIA-AI-IOT/jetbot) package

## Citation

If you use this package in your research, please cite:

```bibtex
@software{remote_robot,
  title = {remote-robot: LeRobot-compatible remote robot control},
  year = {2025},
  url = {https://github.com/ih/remote-robot}
}
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/ih/remote-robot/issues
- LeRobot Discord: https://discord.gg/s3KuuzsPFb
