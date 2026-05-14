from aiogram.fsm.state import State, StatesGroup


class OnboardingState(StatesGroup):
    waiting_phone = State()
    waiting_subscription = State()


class WarmupState(StatesGroup):
    question_1 = State()
    question_2 = State()


class PaymentState(StatesGroup):
    waiting_screenshot = State()   # user must send photo of receipt


class AdminState(StatesGroup):
    entering_decline_reason = State()

class ConsultState(StatesGroup):
    question_1 = State()
    question_2 = State()
