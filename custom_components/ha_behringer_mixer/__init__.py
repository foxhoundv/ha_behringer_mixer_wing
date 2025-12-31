"""Custom integration to integrate a Behringer mixer into Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import BehringerMixerApiClient
from .const import DOMAIN, LOGGER
from .coordinator import MixerDataUpdateCoordinator
from .automation_recorder import AutomationRecorder
from .automation_player import AutomationPlayer

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SELECT,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})
    try:
        client = BehringerMixerApiClient(
            mixer_ip=entry.data["MIXER_IP"], mixer_type=entry.data["MIXER_TYPE"]
        )
        if not await client.setup():
            raise ConfigEntryNotReady(
                f"Timeout while connecting to {entry.data['MIXER_IP']}"
            )

        hass.data[DOMAIN][entry.entry_id] = coordinator = MixerDataUpdateCoordinator(
            hass=hass,
            client=client,
        )
        await coordinator.async_config_entry_first_refresh()
        client.register_coordinator(coordinator)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    except Exception as e:
        LOGGER.error("Failed to set up entry: %s", e)
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""

    if entry.entry_id not in hass.data.get(DOMAIN, {}):
        LOGGER.warning("Attempted to unload an entry that was never loaded: %s", entry.entry_id)
        return False

    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await hass.data[DOMAIN][entry.entry_id].client.stop()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version < 2:
        """Update Config data to include valid channels/bussses etc."""
        client = BehringerMixerApiClient(
            mixer_ip=config_entry.data.get("MIXER_IP"),
            mixer_type=config_entry.data.get("MIXER_TYPE"),
        )
        await client.setup(test_connection_only=True)
        await client.async_get_data()
        await client.stop()
        mixer_info = client.mixer_info()
        new = {**config_entry.data}
        new["CHANNEL_CONFIG"] = list(
            range(1, mixer_info.get("channel", {}).get("number") + 1)
        )
        new["BUS_CONFIG"] = list(range(1, mixer_info.get("bus", {}).get("number") + 1))
        new["DCA_CONFIG"] = list(range(1, mixer_info.get("dca", {}).get("number") + 1))
        new["MATRIX_CONFIG"] = list(
            range(1, mixer_info.get("matrix", {}).get("number") + 1)
        )
        new["AUXIN_CONFIG"] = list(
            range(1, mixer_info.get("auxin", {}).get("number") + 1)
        )
        new["MAIN_CONFIG"] = True
        new["CHANNELSENDS_CONFIG"] = False
        new["BUSSENDS_CONFIG"] = False
        hass.config_entries.async_update_entry(config_entry, data=new, version =2)
    if config_entry.version < 3:
        new = {**config_entry.data}
        new["DBSENSORS"] = True
        new["UPSCALE_100"] = False
        hass.config_entries.async_update_entry(config_entry, data=new, version =3)
    if config_entry.version < 4:
        new = {**config_entry.data}
        new["HEADAMPS_CONFIG"] = 0
        hass.config_entries.async_update_entry(config_entry, data=new, version =4)

    LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True

class BehringerWingMixer:
    def __init__(self, ...):
        # ... existing code ...
        self.automation_recorder = AutomationRecorder()
        self.automation_player = AutomationPlayer(self.osc_client)
        self.armed_channels = set()  # Channels enabled for automation
        
    async def async_setup_services(self):
        """Register automation services"""
        
        async def handle_record_start(call):
            project_name = call.data.get("project_name")
            initial_state = await self._capture_current_state()
            self.automation_recorder.start_recording(initial_state)
            
        async def handle_record_stop(call):
            save_path = call.data.get("save_path")
            automation_data = self.automation_recorder.stop_recording()
            await self._save_automation(save_path, automation_data)
            
        async def handle_play_automation(call):
            automation_file = call.data.get("automation_file")
            from_position = call.data.get("from_position", 0.0)
            await self.automation_player.load_automation(automation_file)
            await self.automation_player.start_playback(from_position)
            
        async def handle_stop_automation(call):
            await self.automation_player.stop_playback()
            
        async def handle_arm_channels(call):
            channels = self._parse_channel_list(call.data.get("channels", ""))
            buses = self._parse_channel_list(call.data.get("buses", ""))
            enable = call.data.get("enable", True)
            
            if enable:
                self.armed_channels.update(channels)
                self.armed_channels.update([(b, "bus") for b in buses])
            else:
                self.armed_channels.difference_update(channels)
                self.armed_channels.difference_update([(b, "bus") for b in buses])
        
        # Register services
        self.hass.services.async_register(
            DOMAIN, "record_automation_start", handle_record_start
        )
        self.hass.services.async_register(
            DOMAIN, "record_automation_stop", handle_record_stop
        )
        self.hass.services.async_register(
            DOMAIN, "play_automation", handle_play_automation
        )
        self.hass.services.async_register(
            DOMAIN, "stop_automation", handle_stop_automation
        )
        self.hass.services.async_register(
            DOMAIN, "automation_arm_channels", handle_arm_channels
        )
