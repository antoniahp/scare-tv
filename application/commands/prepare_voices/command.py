class PrepareVoicesCommand:
    """Prepares the live-scare voices (only the missing or outdated ones)."""

    def __init__(self, voice_service):
        self.voice_service = voice_service

    def execute(self, dto):
        return self.voice_service.build(dto.folder, dto.lang, again=dto.again)
