from typing import Tuple, List

from sqlalchemy.orm import Session

from db import engine
from db.model import Configuration


class CONFIGURATION_KEYS(object):
    CS_INSTALL_DIR = "cs.install.dir"
    CS_DATA_DIR = "cs.data.dir"


def get_configuration(key: str) -> Configuration:
    with Session(engine) as sess:
        return sess.query(Configuration).filter_by(key=key).first()


def get_all_configurations() -> list[Configuration]:
    with Session(engine) as sess:
        return sess.query(Configuration).all()


def set_configuration(key, value):
    with Session(engine) as sess:
        config = get_configuration(key)
        if not config:
            config = Configuration(key, value)
            sess.add(config)
        else:
            config.value = value

        sess.commit()


def set_configuration_list(key_value_tuples_list: List[Tuple[str, str]]):
    with Session(engine) as sess:
        for key, value in key_value_tuples_list:
            # we repeat the code of set_configuration to avoid to make multiple commits
            config = get_configuration(key)
            if not config:
                config = Configuration(key, value)
                sess.add(config)
            else:
                config.value = value

        sess.commit()


def set_configuration_object(key_value_object: dict):
    set_configuration_list([(key, value) for key, value in key_value_object.items()])

