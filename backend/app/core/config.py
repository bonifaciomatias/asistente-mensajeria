from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./asistente.db"
    api_token: str = "cambiame-en-produccion"
    telegram_bot_token: str = "9251853651:AAHlu4DdmCM4CcmfB52TijFAvZUtfEX_mDA"
    log_level: str = "INFO"

    summarize_threshold_tokens: int = 4000
    summary_target_tokens: int = 600

    # Ventana horaria de operación
    business_timezone: str = "America/Mexico_City"
    business_hours_start: int = 9
    business_hours_end: int = 24

    # Límites
    daily_limit_global: int = 40
    daily_limit_per_contact: int = 20
    warmup_max_auto_replies: int = 2

    class Config:
        env_file = ".env"

    groq_api_key: str = "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"
    groq_model: str = "qwen/qwen3.8-27b"  # ← verificar nombre exacto en console.groq.com/docs/models
    max_context_tokens: int = 6000

    # Envío
    send_mode: str = "xdotool"            # bot_api | xdotool
    xdotool_char_delay_ms: tuple[int, int] = (80, 130)  # rango por carácter
    xdotool_chunk_chars: tuple[int, int] = (15, 40)     # tamaño de fragmento
    xdotool_chunk_pause_s: tuple[float, float] = (0.2, 0.6)  # pausa entre fragmentos
    xdotool_enter_grace_s: float = 1.0     # espera antes del Enter
    xdotool_window_keyword: str = "firefox"  # substring esperado en el nombre de la ventana activa


settings = Settings()