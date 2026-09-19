from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    FRONTEND_URL: str = "http://127.0.0.1:5500"

              
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""
    FIREBASE_CREDENTIALS_PATH: str = ""

                                                                       
                                                                             
                                                
    FIREBASE_WEB_API_KEY: str = ""
    FIREBASE_AUTH_DOMAIN: str = ""
    FIREBASE_STORAGE_BUCKET: str = ""
    FIREBASE_MESSAGING_SENDER_ID: str = ""
    FIREBASE_APP_ID: str = ""

        
    GEMINI_API_KEY: str = ""

                                        
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_STT_MODEL: str = "scribe_v2"

                                                                      
                                                                  
                                                                      
                                                   
    MOCK_AI: bool = True

             
    MOCK_WHISPER: bool = True

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()