"""Состояния FSM."""

from aiogram.fsm.state import State, StatesGroup


class OrderFlow(StatesGroup):
    waiting_proof = State()


class AddKeys(StatesGroup):
    waiting = State()
