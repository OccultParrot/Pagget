import os
import json
import pathlib
import traceback

import dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import models

dotenv.load_dotenv()


class DatabaseClient:
    def __init__(self):
        db_url = os.getenv('DATABASE_URL')
        self.engine = create_engine(db_url)

    def get_berries(self, server_id: int) -> list[models.User]:
        try:
            with Session(self.engine) as session:
                result = session.execute(text(
                    f"SELECT * FROM berries WHERE server_id = :server_id"
                ), {"server_id": server_id})
                return [models.User(
                    id=u.id,
                    server_id=server_id,
                    balance=u.balance,
                ) for u in result.fetchall()]
        except Exception as e:
            print(f"An exception occurred with querying server berries balances: {e}")
            return []

    def get_berries_balance(self, user_id: int, server_id: int) -> int:
        try:
            with Session(self.engine) as session:
                result = session.execute(
                    text(f"SELECT balance FROM berries WHERE id = :user_id AND server_id = :server_id"),
                    {
                        'user_id': user_id,
                        'server_id': server_id
                    })
                row = result.fetchone()
                if row is None:
                    server = self.get_server(server_id)
                    session.execute(text(
                        "INSERT INTO berries (id, server_id, balance) VALUES (:id, :server_id, :balance)"
                    ), {
                        'id': user_id,
                        'server_id': server_id,
                        'balance': server.starting_pay
                    })
                    session.commit()
                    return server.starting_pay
                return row[0]
        except Exception as e:
            print(f"An exception occurred with querying berries balance: {e}")
            return 0

    def set_berries_balance(self, user_id: int, server_id: int, berries_balance: int) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "INSERT INTO berries (id, server_id, balance) VALUES (:user_id, :server_id, :balance) "
                    "ON CONFLICT (id, server_id) DO UPDATE SET balance = :balance"),
                    {
                        "user_id": user_id,
                        "server_id": server_id,
                        "balance": berries_balance
                    })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with setting berries balance: {e}")

    def add_berries_balance(self, user_id: int, server_id: int, amount: int) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "INSERT INTO berries (id, server_id, balance) VALUES (:user_id, :server_id, :amount) "
                    "ON CONFLICT (id, server_id) DO UPDATE SET balance = berries.balance + :amount"
                ), {
                    "user_id": user_id,
                    "server_id": server_id,
                    "amount": amount
                })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with adding berries balance: {e}")

    def get_afflictions(self, server_id: int) -> list[models.Affliction]:
        try:
            with Session(self.engine) as session:
                result = session.execute(text(
                    "SELECT id, server_id, title, description, rarity, is_minor, is_birth_defect, seasons "
                    "FROM afflictions WHERE server_id = :server_id"
                ),
                    {
                        "server_id": server_id
                    }
                )
                afflictions = result.fetchall()
                return [models.Affliction(
                    id=a.id,
                    server_id=a.server_id,
                    title=a.title,
                    description=a.description,
                    rarity=models.Rarity(a.rarity),
                    is_minor=a.is_minor,
                    is_birth_defect=a.is_birth_defect,
                    seasons=[models.Season(s) for s in a.seasons]
                ) for a in afflictions]

        except Exception as e:
            print(f"An exception occurred with querying afflictions: {e}")
            return []

    def get_affliction(self, affliction_id: int) -> models.Affliction | None:
        try:
            with Session(self.engine) as session:
                result = session.execute(text(
                    "SELECT * FROM afflictions WHERE id = :affliction_id"
                ),
                    {
                        "affliction_id": affliction_id
                    })
                affliction = result.fetchone()
                return models.Affliction(
                    id=affliction.id,
                    server_id=affliction.server_id,
                    title=affliction.title,
                    description=affliction.description,
                    rarity=models.Rarity(affliction.rarity),
                    is_minor=affliction.is_minor,
                    is_birth_defect=affliction.is_birth_defect,
                    seasons=[models.Season(s) for s in affliction.seasons]
                )
        except Exception as e:
            print(f"An exception occurred with querying affliction: {e}")
            return None

    def add_affliction(self, server_id: int, affliction: models.Affliction) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "INSERT INTO afflictions (server_id, title, description, rarity, is_minor, is_birth_defect, seasons) "
                    "VALUES (:server_id, :title, :description, :rarity, :is_minor, :is_birth_defect, CAST(:seasons AS season[])) "
                ), {
                    "server_id": server_id,
                    "title": affliction.title,
                    "description": affliction.description,
                    "rarity": affliction.rarity.value,
                    "is_minor": affliction.is_minor,
                    "is_birth_defect": affliction.is_birth_defect,
                    "seasons": "{" + ",".join(s.value if s is not None else "any" for s in affliction.seasons) + "}"  # Serialize Season enums to Postgres array literal
                })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with adding affliction: {e}")

    def edit_affliction(self, server_id: int, affliction_id: int, affliction: models.Affliction) -> None:
        try:
            with Session(self.engine) as session:
                print(affliction.seasons)
                session.execute(text(
                    "INSERT INTO afflictions (id, server_id, title, description, rarity, is_minor, is_birth_defect, seasons) "
                    "VALUES (:id, :server_id, :title, :description, :rarity, :is_minor, :is_birth_defect, CAST(:seasons AS season[])) "
                    "ON CONFLICT (id, server_id) DO UPDATE SET "
                    "title = :title, description = :description, rarity = :rarity, "
                    "is_minor = :is_minor, is_birth_defect = :is_birth_defect, seasons = CAST(:seasons AS season[])"
                ),
                    {
                        "id": affliction_id,
                        "server_id": server_id,
                        "title": affliction.title,
                        "description": affliction.description,
                        "rarity": affliction.rarity.value,
                        "is_minor": affliction.is_minor,
                        "is_birth_defect": affliction.is_birth_defect,
                        "seasons": "{" + ",".join(s.value if s is not None else "any" for s in affliction.seasons) + "}"  # Serialize Season enums to Postgres array literal
                    })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with editing affliction: {e}")

    def remove_affliction(self, affliction_id: int) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "DELETE FROM afflictions WHERE id = :affliction_id"
                ),
                    {
                        "affliction_id": affliction_id
                    })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with removing affliction: {e}")

    def get_servers(self) -> list[models.Server]:
        try:
            with Session(self.engine) as session:
                result = session.execute(text(
                    "SELECT id, name, affliction_chance, minor_affliction_chance FROM servers"
                ))
                servers = result.fetchall()
                return [models.Server(
                    id=s.id,
                    name=s.name,
                    affliction_chance=s.affliction_chance,
                    minor_affliction_chance=s.minor_affliction_chance
                ) for s in servers]
        except Exception as e:
            print(f"An exception occurred with querying servers: {e}")
            return []

    def get_server(self, server_id: int, server_name: str) -> models.Server | None:
        try:
            with Session(self.engine) as session:
                result = session.execute(
                    text("SELECT * FROM servers WHERE id = :server_id"),
                    {"server_id": server_id}
                )
                server = result.fetchone()

                if server is None:
                    return self.create_new_server(server_id, server_name)

                return models.Server(
                    id=server_id,
                    name=server.name,
                    affliction_chance=server.affliction_chance,
                    minor_affliction_chance=server.minor_affliction_chance,
                    starting_pay=server.starting_pay,
                    minimum_bet=server.minimum_bet,
                )
        except Exception as e:
            print(f"An exception occurred with querying server: {e}")
            return None

    def add_server(self, server: models.Server) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "INSERT INTO servers (id, name, affliction_chance, minor_affliction_chance, starting_pay, minimum_bet) "
                    "VALUES (:id, :name, :affliction_chance, :minor_affliction_chance, :starting_pay, :minimum_bet) "
                    "ON CONFLICT (id) "
                    "DO UPDATE SET name = :name, affliction_chance = :affliction_chance, minor_affliction_chance = :minor_affliction_chance, starting_pay = :starting_pay, minimum_bet = :minimum_bet",
                ),
                    {
                        "id": server.id,
                        "name": server.name,
                        "affliction_chance": server.affliction_chance,
                        "minor_affliction_chance": server.minor_affliction_chance,
                        "starting_pay": server.starting_pay,
                        "minimum_bet": server.minimum_bet
                    })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with adding server: {e}")

    def remove_server(self, server_id: int) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "DELETE FROM servers WHERE id = :server_id"
                ),
                    {
                        "server_id": server_id
                    })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with removing server: {e}")

    def get_gather_outcomes(self, server_id: int) -> list[models.GatherOutcome]:
        try:
            with Session(self.engine) as session:
                result = session.execute(text(
                    "SELECT id, server_id, description, rarity, is_robbery, value "
                    "FROM gather_outcomes WHERE server_id = :server_id"
                ), {
                    "server_id": server_id
                })
                outcomes = result.fetchall()
                return [models.GatherOutcome(
                    id=o.id,
                    server_id=o.server_id,
                    description=o.description,
                    rarity=models.Rarity(o.rarity),
                    is_robbery=o.is_robbery,
                    value=o.value
                ) for o in outcomes]
        except Exception as e:
            print(f"An exception occurred with querying gather outcomes: {e}")
            return []

    def get_gather_outcome(self, outcome_id: int) -> models.GatherOutcome | None:
        try:
            with Session(self.engine) as session:
                result = session.execute(text(
                    "SELECT * FROM gather_outcomes WHERE id = :outcome_id"
                ), {
                    "outcome_id": outcome_id
                })
                outcome = result.fetchone()
                return models.GatherOutcome(
                    id=outcome.id,
                    server_id=outcome.server_id,
                    description=outcome.description,
                    rarity=models.Rarity(outcome.rarity),
                    is_robbery=outcome.is_robbery,
                    value=outcome.value
                )
        except Exception as e:
            print(f"An exception occurred with querying gather outcome: {e}")
            return None

    def add_gather_outcome(self, server_id: int, outcome: models.GatherOutcome) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "INSERT INTO gather_outcomes (server_id, description, rarity, is_robbery, value) "
                    "VALUES (:server_id, :description, :rarity, :is_robbery, :value)"
                ), {
                    "server_id": server_id,
                    "description": outcome.description,
                    "rarity": outcome.rarity.value,
                    "is_robbery": outcome.is_robbery,
                    "value": outcome.value
                })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with adding gather outcome: {e}")

    def edit_gather_outcome(self, outcome_id: int, outcome: models.GatherOutcome) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "UPDATE gather_outcomes SET "
                    "description = :description, rarity = :rarity, is_robbery = :is_robbery, value = :value "
                    "WHERE id = :outcome_id"
                ), {
                    "outcome_id": outcome_id,
                    "description": outcome.description,
                    "rarity": outcome.rarity.value,
                    "is_robbery": outcome.is_robbery,
                    "value": outcome.value
                })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with editing gather outcome: {e}")

    def remove_gather_outcome(self, outcome_id: int) -> None:
        try:
            with Session(self.engine) as session:
                session.execute(text(
                    "DELETE FROM gather_outcomes WHERE id = :outcome_id"
                ), {
                    "outcome_id": outcome_id
                })
                session.commit()
        except Exception as e:
            print(f"An exception occurred with removing gather outcome: {e}")

    def create_new_server(self, server_id: int, server_name: str) -> models.Server:
        try:
            afflictions: list[models.Affliction] = []
            hunts: list[models.GatherOutcome] = []
            steals: list[models.GatherOutcome] = []

            for d in json.loads(pathlib.Path("./defaults/default-hunts.json").read_text()):
                hunts.append(
                    models.GatherOutcome(
                        description=d.get("description"),
                        rarity=models.Rarity(d.get("rarity")),
                        is_robbery=d.get("is_robbery"),
                        value=d.get("value"),
                        server_id=server_id,
                        id=0  # Gets discarded
                    )
                )

            for d in json.loads(pathlib.Path("./defaults/default-steals.json").read_text()):
                steals.append(
                    models.GatherOutcome(
                        description=d.get("description"),
                        rarity=models.Rarity(d.get("rarity")),
                        is_robbery=d.get("is_robbery"),
                        value=d.get("value"),
                        server_id=server_id,
                        id=0  # Gets discarded
                    )
                )

            for d in json.loads(pathlib.Path("./defaults/default-afflictions.json").read_text()):
                seasons: list[models.Season] = []
                if d.get("seasons") is None:
                    seasons.append(models.Season.ANY)
                else:
                    for s in d.get("seasons"):
                        seasons.append(models.Season(s))

                afflictions.append(
                    models.Affliction(
                        title=d.get("name"),
                        description=d.get("description"),
                        rarity=models.Rarity(d.get("rarity")),
                        is_minor=d.get("is_minor"),
                        is_birth_defect=d.get("is_birth_defect"),
                        seasons=seasons,
                        server_id=server_id,
                        id=0  # Gets discarded
                    )
                )

            self.add_server(
                models.Server(
                    id=server_id,
                    name=server_name
                )
            )

            for outcome in hunts:
                self.add_gather_outcome(server_id, outcome)

            for affliction in afflictions:
                self.add_affliction(server_id, affliction)

            print(f"Initialized \"{server_name}\":")
            print(f"\t{len(hunts)} Gather outcomes")
            print(f"\t{len(afflictions)} Afflictions")

            return models.Server(
                id=server_id,
                name=server_name
            )
        except Exception as e:
            print(f"An exception occurred with adding a server: {e}")
            print(traceback.format_exc())
