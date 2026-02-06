import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()
basedir = Path(__file__).resolve().parent.parent.parent
print(f"どこdir: {basedir}")


# 環境変数 DATABASE_URL が設定されていればそれを使用、なければMySQL環境変数をチェック
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # DATABASE_URL が設定されている場合、それを使用
    DB_URL = DATABASE_URL
    print(f"Using DATABASE_URL: {DB_URL}")
elif (
    os.getenv("DB_USER")
    and os.getenv("DB_PASSWORD")
    and os.getenv("DB_HOST")
    and os.getenv("DB_PORT")
    and os.getenv("DB_NAME")
):
    # MySQL接続用の環境変数が全て設定されている場合、それを使用
    DB_URL = "mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4".format(
        **{
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "db_name": os.getenv("DB_NAME"),
        }
    )
    print("Using MySQL database from environment variables.")
else:
    # どちらも設定されていない場合、テスト用にSQLiteを使用
    DB_FILE = os.path.join(basedir, "test.db")
    DB_URL = f"sqlite:///{DB_FILE}"
    print(f"Using SQLite database for testing: {DB_FILE}")


engine = create_engine(DB_URL, echo=False)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = Session()

Base = declarative_base()


# 初期化関数を追加
def init_db():
    Base.metadata.create_all(bind=engine)
