"""
FSM States for registration flow.
"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """States for registration process."""
    
    # Initial states
    asking_team_member = State()  # Asking if user is team member
    asking_position = State()      # Asking about position
    
    # Dynamic question answering
    answering_questions = State()  # Answering questions from database
