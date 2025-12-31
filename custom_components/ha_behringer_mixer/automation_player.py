import asyncio
from typing import Dict, List, Callable
import json

class AutomationPlayer:
    """Plays back recorded mixer automation"""
    
    def __init__(self, osc_client):
        self.osc_client = osc_client
        self.is_playing = False
        self.playback_task = None
        self.current_position = 0.0
        self.automation_data = None
        
    async def load_automation(self, automation_file: str):
        """Load automation data from file"""
        with open(automation_file, 'r') as f:
            self.automation_data = json.load(f)
            
    async def start_playback(self, from_position: float = 0.0):
        """Start playing automation from specified position"""
        if not self.automation_data:
            raise ValueError("No automation data loaded")
            
        self.is_playing = True
        self.current_position = from_position
        
        # Apply initial state if starting from beginning
        if from_position == 0.0:
            await self._apply_initial_state()
        
        # Start playback task
        self.playback_task = asyncio.create_task(
            self._playback_loop()
        )
        
    async def stop_playback(self):
        """Stop automation playback"""
        self.is_playing = False
        if self.playback_task:
            self.playback_task.cancel()
            
    async def _apply_initial_state(self):
        """Apply initial mixer state before playback"""
        initial = self.automation_data.get("initial_state", {})
        
        for key, value in initial.items():
            # Parse key format: "ch_1_fader", "bus_2_mute", etc.
            parts = key.split("_")
            channel_type = parts[0]
            channel_num = int(parts[1])
            param_type = parts[2]
            
            await self._send_osc_command(
                channel_type, channel_num, param_type, value
            )
            
    async def _playback_loop(self):
        """Main playback loop that sends events at correct times"""
        events = self.automation_data.get("events", [])
        start_time = asyncio.get_event_loop().time()
        
        for event in events:
            if not self.is_playing:
                break
                
            # Skip events before current position
            if event["timestamp"] < self.current_position:
                continue
                
            # Calculate wait time
            target_time = event["timestamp"] - self.current_position
            current_elapsed = asyncio.get_event_loop().time() - start_time
            wait_time = target_time - current_elapsed
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                
            # Send OSC command
            await self._send_osc_command(
                event["channel_type"],
                event["channel_num"],
                event["param_type"],
                event["value"]
            )
            
            self.current_position = event["timestamp"]
            
    async def _send_osc_command(self, channel_type: str, channel_num: int,
                                param_type: str, value: float):
        """Send OSC command to Wing mixer"""
        osc_paths = {
            "fader": f"/{channel_type}/{channel_num}/fdr",
            "mute": f"/{channel_type}/{channel_num}/mute",
            "pan": f"/{channel_type}/{channel_num}/pan"
        }
        
        path = osc_paths.get(param_type)
        if path:
            await self.osc_client.send_command(path, value)
