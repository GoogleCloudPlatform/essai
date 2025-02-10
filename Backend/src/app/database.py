# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from sqlmodel import SQLModel, Session, create_engine, text
import pg8000
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy.engine.base import Engine

from app.config import settings

log = logging.getLogger("uvicorn")


def connect_with_connector() -> Engine:
    instance_connection_name = settings.INSTANCE_CONNECTION_NAME
    db_user = settings.IAM_USER
    db_name = settings.POSTGRES_DB

    ip_type = IPTypes.PRIVATE

    # initialize Cloud SQL Python Connector object
    connector = Connector(ip_type)

    def getconn() -> pg8000.dbapi.Connection:
        conn: pg8000.dbapi.Connection = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            db=db_name,
            enable_iam_auth=True,
            ip_type=ip_type,
        )
        return conn

    pool = create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,  # 30 minutes
    )
    return pool


engine = connect_with_connector()


def create_db_and_tables():
    log.info("Creating (if not exists) database tables...")
    SQLModel.metadata.create_all(engine)


def drop_all_tables():
    with Session(bind=engine) as session:
        for t in ["requisicao", "correcoes", "feedback"]:
            log.warning(f"droping table - {t}")
            session.exec(text(f"DROP TABLE {t} CASCADE"))
            session.commit()
            log.warning("done")
