"""Layer 6: Procedural Memory -- learned routines from repeated patterns."""

from __future__ import annotations

from datetime import datetime

from brain.src.cognitive.models import Procedure, ProcedureStatus, TriggerType
from brain.src.db.repositories import ProcedureRepo
from brain.src.logger import get_logger

log = get_logger("procedural")


class ProceduralMemory:
    """Detects and manages learned action sequences (routines)."""

    async def suggest_routine(
        self,
        name: str,
        steps: list[dict],
        trigger_description: str = "",
        trigger_type: TriggerType = TriggerType.VERBAL,
        trigger_conditions: dict | None = None,
        target_devices: list[str] | None = None,
    ) -> Procedure:
        procedure = Procedure(
            name=name,
            steps=steps,
            trigger_description=trigger_description,
            trigger_type=trigger_type,
            trigger_conditions=trigger_conditions or {},
            target_devices=target_devices or [],
            status=ProcedureStatus.SUGGESTED,
            times_detected=1,
        )
        result = await ProcedureRepo.create(procedure)
        log.info("routine_suggested", id=result.id, name=name)
        return result

    async def confirm_routine(self, procedure_id: str) -> None:
        await ProcedureRepo.update_status(procedure_id, ProcedureStatus.CONFIRMED)
        log.info("routine_confirmed", id=procedure_id)

    async def activate_routine(self, procedure_id: str) -> None:
        await ProcedureRepo.update_status(procedure_id, ProcedureStatus.ACTIVE)
        log.info("routine_activated", id=procedure_id)

    async def disable_routine(self, procedure_id: str) -> None:
        await ProcedureRepo.update_status(procedure_id, ProcedureStatus.DISABLED)
        log.info("routine_disabled", id=procedure_id)

    async def get_active_routines(self) -> list[Procedure]:
        return await ProcedureRepo.get_active()

    async def match_trigger(self, text: str) -> Procedure | None:
        """Check if input text matches any active routine's trigger."""
        routines = await self.get_active_routines()
        text_lower = text.lower()
        for routine in routines:
            if routine.trigger_description and routine.trigger_description.lower() in text_lower:
                return routine
            conditions = routine.trigger_conditions
            if conditions.get("phrase") and conditions["phrase"].lower() in text_lower:
                return routine
        return None
