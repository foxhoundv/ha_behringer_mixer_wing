from datetime import datetime
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class AutomationEventType(Enum):
    FADER = "fader"
    MUTE = "mute"
    PAN = "pan"

class ChannelType(Enum):
    CHANNEL = "ch"
    BUS = "bus"
    MAIN = "main"

@dataclass
class AutomationEvent:
    timestamp: float  # Seconds since recording start
    channel_type: str  # "ch", "bus", "main"
    channel_num: int
    param_type: str   # "fader", "mute", "pan"
    value: float      # dB for fader, 0/1 for mute, -1 to 1 for pan
    
    def to_dict(self):
        return asdict(self)

class AutomationRecorder:
    """Records mixer parameter changes with timestamps"""
    
    def __init__(self):
        self.events: List[AutomationEvent] = []
        self.is_recording = False
        self.start_time: Optional[float] = None
        self.initial_state: Dict = {}
        
    def start_recording(self, initial_state: Dict):
        """Begin recording automation data"""
        self.is_recording = True
        self.start_time = datetime.now().timestamp()
        self.events = []
        self.initial_state = initial_state
        
    def stop_recording(self) -> Dict:
        """Stop recording and return automation data"""
        self.is_recording = False
        return {
            "initial_state": self.initial_state,
            "events": [event.to_dict() for event in self.events],
            "duration": self.get_elapsed_time()
        }
        
    def record_event(self, channel_type: str, channel_num: int, 
                     param_type: str, value: float):
        """Record a parameter change"""
        if not self.is_recording:
            return
            
        timestamp = self.get_elapsed_time()
        event = AutomationEvent(
            timestamp=timestamp,
            channel_type=channel_type,
            channel_num=channel_num,
            param_type=param_type,
            value=value
        )
        self.events.append(event)
        
    def get_elapsed_time(self) -> float:
        """Get time elapsed since recording started"""
        if self.start_time is None:
            return 0.0
        return datetime.now().timestamp() - self.start_time
