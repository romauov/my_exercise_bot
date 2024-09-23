from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()
class Secrets(BaseSettings):
    tg_token: str
    my_tg_id: int
    
    class Config:  
        env_file = ".env"  
        env_file_encoding = "utf-8" 

secrets = Secrets()