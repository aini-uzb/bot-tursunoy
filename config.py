import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
FREE_CHANNEL_ID: str = os.getenv("FREE_CHANNEL_ID", "")

# Click
CLICK_SERVICE_ID: str = os.getenv("CLICK_SERVICE_ID", "")
CLICK_MERCHANT_ID: str = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SECRET_KEY: str = os.getenv("CLICK_SECRET_KEY", "")
CLICK_MERCHANT_USER_ID: str = os.getenv("CLICK_MERCHANT_USER_ID", "")

# Payme
PAYME_MERCHANT_ID: str = os.getenv("PAYME_MERCHANT_ID", "")
PAYME_KEY: str = os.getenv("PAYME_KEY", "")
PAYME_URL: str = os.getenv("PAYME_URL", "https://checkout.paycom.uz")

ADMIN_IDS: list[int] = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

# AmoCRM
AMOCRM_DOMAIN: str = os.getenv("AMOCRM_DOMAIN", "")
AMOCRM_CLIENT_ID: str = os.getenv("AMOCRM_CLIENT_ID", "")
AMOCRM_CLIENT_SECRET: str = os.getenv("AMOCRM_CLIENT_SECRET", "")
AMOCRM_REDIRECT_URI: str = os.getenv("AMOCRM_REDIRECT_URI", "")
AMOCRM_ACCESS_TOKEN: str = os.getenv("AMOCRM_ACCESS_TOKEN", "")
AMOCRM_REFRESH_TOKEN: str = os.getenv("AMOCRM_REFRESH_TOKEN", "")

# Хештеги для автобродкаста — 3 смысла на 3 языках (RU/EN/UZ), все запускают
# одну и ту же рассылку. Пост с любым из этих тегов пересылается каждому
# пользователю ровно один раз, даже если в посте несколько тегов сразу.
_DEFAULT_HASHTAGS = (
    "#поступление,#учёба,#студент,"
    "#admission,#study,#student,"
    "#qabul,#oqish,#talaba"
)
BROADCAST_HASHTAGS: list[str] = [
    t.strip() for t in os.getenv("BROADCAST_HASHTAGS", _DEFAULT_HASHTAGS).split(",")
    if t.strip()
]

# Закрытый канал (подписка, отдельная категория)
CHANNEL_SUBSCRIPTION: dict = {
    "name_ru": "🔒 Закрытый канал",
    "name_uz": "🔒 Yopiq kanal",
    "desc_ru": (
        "🔒 <b>Закрытый канал</b>\n\n"
        "Ежемесячный доступ к закрытому каналу с эксклюзивным контентом.\n\n"
        "✅ Инсайты и разборы каждую неделю\n"
        "✅ Закрытые материалы и документы\n"
        "✅ Прямые эфиры и Q&A с Турсуной\n\n"
        "💰 Стоимость: <b>200,000 сум/мес</b>\n"
        "📅 Доступ: 30 дней\n\n"
        "Нажмите кнопку, чтобы оплатить 👇"
    ),
    "desc_uz": (
        "🔒 <b>Yopiq kanal</b>\n\n"
        "Eksklyuziv kontent bilan yopiq kanalga oylik kirish.\n\n"
        "✅ Har hafta insaytlar va tahlillar\n"
        "✅ Yopiq materiallar va hujjatlar\n"
        "✅ Tursunoy bilan jonli efirlar va Q&A\n\n"
        "💰 Narxi: <b>200,000 so'm/oy</b>\n"
        "📅 Kirish: 30 kun\n\n"
        "To'lash uchun tugmani bosing 👇"
    ),
    "price": 3000,
    "price_display_ru": "3,000 сум/мес",
    "price_display_uz": "3,000 so'm/oy",
    "days": 30,
    "channel_id": os.getenv("CHANNEL_SUBSCRIPTION_ID", ""),
}

# 5 платных курсов
COURSES: dict = {
    "ivy_masters": {
        "name_ru": "🎓 Магистратура Ivy League",
        "name_uz": "🎓 Ivy League magistratura",
        "brief_ru": "Поступление в топ университеты мира — $500 · 90 дней",
        "brief_uz": "Dunyoning top universitetlariga kirish — $500 · 90 kun",
        "desc_ru": (
            "🎓 <b>Магистратура Ivy League</b>\n\n"
            "Полное сопровождение при поступлении в топовые университеты мира.\n\n"
            "✅ Разбор вашего профиля\n"
            "✅ Стратегия поступления\n"
            "✅ Помощь с документами\n\n"
            "💰 Стоимость: <b>$500</b>\n"
            "📅 Доступ: 90 дней\n\n"
            "Нажмите кнопку, чтобы оплатить 👇"
        ),
        "desc_uz": (
            "🎓 <b>Ivy League magistratura</b>\n\n"
            "Dunyoning eng yaxshi universitetlariga kirish uchun to'liq yordam.\n\n"
            "✅ Profilingizni tahlil qilish\n"
            "✅ Kirish strategiyasi\n"
            "✅ Hujjatlar bilan yordam\n\n"
            "💰 Narxi: <b>$500</b>\n"
            "📅 Kirish: 90 kun\n\n"
            "To'lash uchun tugmani bosing 👇"
        ),
        "price": 500,
        "price_uzs": 6500000,
        "days": 90,
        "channel_id": os.getenv("CHANNEL_IVY_MASTERS", ""),
    },
    "motivation_letter": {
        "name_ru": "✍️ Мотивационное письмо (22 нед.)",
        "name_uz": "✍️ Motivatsion xat (22 hafta)",
        "brief_ru": "Essay без ChatGPT, авторский подход — $500 · 90 дней",
        "brief_uz": "ChatGPTsiz essay, muallif yondashuvi — $500 · 90 kun",
        "desc_ru": (
            "✍️ <b>Написание мотивационного письма без ChatGPT</b>\n\n"
            "22-недельная программа по написанию essay.\n\n"
            "✅ Авторский подход без ИИ\n"
            "✅ Индивидуальная обратная связь\n"
            "✅ Доступ к материалам навсегда\n\n"
            "💰 Стоимость: <b>$500</b>\n"
            "📅 Доступ: 90 дней\n\n"
            "Нажмите кнопку, чтобы оплатить 👇"
        ),
        "desc_uz": (
            "✍️ <b>ChatGPTsiz motivatsion xat yozish</b>\n\n"
            "22 haftalik essay yozish dasturi.\n\n"
            "✅ Sun'iy intellektsiz muallif yondashuvi\n"
            "✅ Individual qayta aloqa\n"
            "✅ Materiallarga abadiy kirish\n\n"
            "💰 Narxi: <b>$500</b>\n"
            "📅 Kirish: 90 kun\n\n"
            "To'lash uchun tugmani bosing 👇"
        ),
        "price": 500,
        "price_uzs": 6500000,
        "days": 90,
        "channel_id": os.getenv("CHANNEL_MOTIVATION", ""),
    },
    "activities_bootcamp": {
        "name_ru": "🚀 Activities Bootcamp",
        "name_uz": "🚀 Activities Bootcamp",
        "brief_ru": "Интенсивный буткемп для поступления в IVY — $200 · 30 дней",
        "brief_uz": "IVY ga kirish uchun intensiv bootcamp — $200 · 30 kun",
        "desc_ru": (
            "🚀 <b>Activities Bootcamp</b>\n\n"
            "Интенсивный буткемп для подготовки к поступлению в IVY.\n\n"
            "✅ Групповые занятия\n"
            "✅ Практические задания\n"
            "✅ Поддержка куратора\n\n"
            "💰 Стоимость: <b>$200</b>\n"
            "📅 Доступ: 30 дней\n\n"
            "Нажмите кнопку, чтобы оплатить 👇"
        ),
        "desc_uz": (
            "🚀 <b>Activities Bootcamp</b>\n\n"
            "IVY ga kirish uchun intensiv bootcamp.\n\n"
            "✅ Guruh darslari\n"
            "✅ Amaliy topshiriqlar\n"
            "✅ Kurator yordami\n\n"
            "💰 Narxi: <b>$200</b>\n"
            "📅 Kirish: 30 kun\n\n"
            "To'lash uchun tugmani bosing 👇"
        ),
        "price": 200,
        "price_uzs": 2600000,
        "days": 30,
        "channel_id": os.getenv("CHANNEL_BOOTCAMP", ""),
    },
    "ivy_bachelors": {
        "name_ru": "🏛 Бакалавр IVY",
        "name_uz": "🏛 IVY bakalavr",
        "brief_ru": "Полное сопровождение в бакалавриат IVY — $2000 · 90 дней",
        "brief_uz": "IVY bakalavriatiga to'liq hamrohlik — $2000 · 90 kun",
        "desc_ru": (
            "🏛 <b>Поступление в IVY (бакалавр)</b>\n\n"
            "Комплексная программа поступления в бакалавриат лучших университетов мира.\n\n"
            "✅ Персональный ментор\n"
            "✅ Полное сопровождение от А до Я\n"
            "✅ Стратегия, документы, интервью\n\n"
            "💰 Стоимость: <b>$2000</b>\n"
            "📅 Доступ: 90 дней\n\n"
            "Нажмите кнопку, чтобы оплатить 👇"
        ),
        "desc_uz": (
            "🏛 <b>IVY bakalavriga kirish</b>\n\n"
            "Dunyoning eng yaxshi universitetlari bakalavriatiga kirish uchun kompleks dastur.\n\n"
            "✅ Shaxsiy mentor\n"
            "✅ A dan Z gacha to'liq hamrohlik\n"
            "✅ Strategiya, hujjatlar, intervyu\n\n"
            "💰 Narxi: <b>$2000</b>\n"
            "📅 Kirish: 90 kun\n\n"
            "To'lash uchun tugmani bosing 👇"
        ),
        "price": 2000,
        "price_uzs": 26000000,
        "days": 90,
        "channel_id": os.getenv("CHANNEL_IVY_BACHELORS", ""),
    },
    "research_paper": {
        "name_ru": "📄 Научная статья",
        "name_uz": "📄 Ilmiy maqola",
        "brief_ru": "Публикация в Scopus/WoS, структура и методология — $400 · 90 дней",
        "brief_uz": "Scopus/WoS da nashr, tuzilish va metodologiya — $400 · 90 kun",
        "desc_ru": (
            "📄 <b>Написание научной статьи</b>\n\n"
            "Курс по написанию и публикации научных статей в международных журналах.\n\n"
            "✅ Структура и методология\n"
            "✅ Работа с источниками\n"
            "✅ Публикация в Scopus/WoS\n\n"
            "💰 Стоимость: <b>$400</b>\n"
            "📅 Доступ: 90 дней\n\n"
            "Нажмите кнопку, чтобы оплатить 👇"
        ),
        "desc_uz": (
            "📄 <b>Ilmiy maqola yozish</b>\n\n"
            "Xalqaro jurnallarda ilmiy maqolalar yozish va nashr etish kursi.\n\n"
            "✅ Tuzilish va metodologiya\n"
            "✅ Manbalar bilan ishlash\n"
            "✅ Scopus/WoS da nashr\n\n"
            "💰 Narxi: <b>$400</b>\n"
            "📅 Kirish: 90 kun\n\n"
            "To'lash uchun tugmani bosing 👇"
        ),
        "price": 400,
        "price_uzs": 5200000,
        "days": 90,
        "channel_id": os.getenv("CHANNEL_RESEARCH", ""),
    },
}
