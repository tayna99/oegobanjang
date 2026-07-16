from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """단일 진실원 — 레거시 결함 §12-17("Base 이중 정의")을 만들지 않는다.

    모든 모델은 이 Base 하나만 상속한다. 두 번째 DeclarativeBase를 만들지 않는다.
    """
