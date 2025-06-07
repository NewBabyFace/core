"""Class to hold all lock accessories."""

import logging
from typing import Any

from pyhap.const import CATEGORY_DOOR_LOCK

from menuai.components.lock import DOMAIN as LOCK_DOMAIN, LockState
from menuai.const import ATTR_CODE, ATTR_ENTITY_ID, STATE_UNKNOWN
from menuai.core import State, callback

from .accessories import TYPES
from .const import CHAR_LOCK_CURRENT_STATE, CHAR_LOCK_TARGET_STATE, SERV_LOCK
from .doorbell import HomeDoorbellAccessory

_LOGGER = logging.getLogger(__name__)

menuai_TO_HOMEKIT_CURRENT = {
    LockState.UNLOCKED.value: 0,
    LockState.UNLOCKING.value: 1,
    LockState.LOCKING.value: 0,
    LockState.LOCKED.value: 1,
    LockState.JAMMED.value: 2,
    STATE_UNKNOWN: 3,
}

menuai_TO_HOMEKIT_TARGET = {
    LockState.UNLOCKED.value: 0,
    LockState.UNLOCKING.value: 0,
    LockState.LOCKING.value: 1,
    LockState.LOCKED.value: 1,
}

VALID_TARGET_STATES = {
    LockState.LOCKING.value,
    LockState.UNLOCKING.value,
    LockState.LOCKED.value,
    LockState.UNLOCKED.value,
}

HOMEKIT_TO_menuai = {
    0: LockState.UNLOCKED.value,
    1: LockState.LOCKED.value,
    2: LockState.JAMMED.value,
    3: STATE_UNKNOWN,
}

STATE_TO_SERVICE = {
    LockState.LOCKING.value: "unlock",
    LockState.LOCKED.value: "lock",
    LockState.UNLOCKING.value: "lock",
    LockState.UNLOCKED.value: "unlock",
}


@TYPES.register("Lock")
class Lock(HomeDoorbellAccessory):
    """Generate a Lock accessory for a lock entity.

    The lock entity must support: unlock and lock.
    """

    def __init__(self, *args: Any) -> None:
        """Initialize a Lock accessory object."""
        super().__init__(*args, category=CATEGORY_DOOR_LOCK)
        self._code = self.config.get(ATTR_CODE)
        state = self.menuai.states.get(self.entity_id)
        assert state is not None

        serv_lock_mechanism = self.add_preload_service(SERV_LOCK)
        self.char_current_state = serv_lock_mechanism.configure_char(
            CHAR_LOCK_CURRENT_STATE, value=menuai_TO_HOMEKIT_CURRENT[STATE_UNKNOWN]
        )
        self.char_target_state = serv_lock_mechanism.configure_char(
            CHAR_LOCK_TARGET_STATE,
            value=menuai_TO_HOMEKIT_CURRENT[LockState.LOCKED.value],
            setter_callback=self.set_state,
        )
        self.async_update_state(state)

    def set_state(self, value: int) -> None:
        """Set lock state to value if call came from HomeKit."""
        _LOGGER.debug("%s: Set state to %d", self.entity_id, value)

        menuai_value = HOMEKIT_TO_menuai[value]
        service = STATE_TO_SERVICE[menuai_value]

        params = {ATTR_ENTITY_ID: self.entity_id}
        if self._code:
            params[ATTR_CODE] = self._code
        self.async_call_service(LOCK_DOMAIN, service, params)

    @callback
    def async_update_state(self, new_state: State) -> None:
        """Update lock after state changed."""
        menuai_state = new_state.state
        current_lock_state = menuai_TO_HOMEKIT_CURRENT.get(
            menuai_state, menuai_TO_HOMEKIT_CURRENT[STATE_UNKNOWN]
        )
        target_lock_state = menuai_TO_HOMEKIT_TARGET.get(menuai_state)
        _LOGGER.debug(
            "%s: Updated current state to %s (current=%d) (target=%s)",
            self.entity_id,
            menuai_state,
            current_lock_state,
            target_lock_state,
        )
        # LockTargetState only supports locked and unlocked
        # Must set lock target state before current state
        # or there will be no notification
        if target_lock_state is not None:
            self.char_target_state.set_value(target_lock_state)

        # Set lock current state ONLY after ensuring that
        # target state is correct or there will be no
        # notification
        self.char_current_state.set_value(current_lock_state)
