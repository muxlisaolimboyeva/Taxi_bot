
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler
)

import sqlite3, datetime, math, requests


TOKEN = "token"
ADMIN_ID = 6738077306
DRIVERS = [1234567899]

db = sqlite3.connect("taxi.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    phone TEXT,
    from_loc TEXT,
    to_loc TEXT,
    tarif TEXT,
    distance REAL,
    price INTEGER,
    status TEXT,
    driver_id INTEGER,
    created_at TEXT
)
""")

db.commit()
NAME, PHONE, FROM, TO, TARIF, COMMENT, CONFIRM = range(7)

main_menu = ReplyKeyboardMarkup([
    ["🚕 Taksi chaqirish"],
    ["📦 Buyurtmalarim", "💰 Tariflar"],
    ["⚙ Sozlamalar", "🆘 Yordam"]
], resize_keyboard=True)

admin_menu = ReplyKeyboardMarkup([
    ["📦 Buyurtmalar"],
    ["🚗 Driverlar"],
    ["📊 Statistika"]
], resize_keyboard=True)

from_ = ReplyKeyboardMarkup([
    [KeyboardButton("📍 Lokatsiya", request_location=True)]
], resize_keyboard=True)

tarif_ = ReplyKeyboardMarkup([
    ["🚕 Ekonom", "🚘 Komfort"]
], resize_keyboard=True)

TARIFLAR = {
    "🚕 Ekonom": {"base": 5000, "per_km": 8000},
    "🚘 Komfort": {"base": 8000, "per_km": 10000}
}

STATUS_PENDING = "⏳ Kutilmoqda"
STATUS_ACCEPTED = "🚗 Haydovchi biriktirildi"
STATUS_ONWAY = "🛣 Yo‘lda"
STATUS_ARRIVED = "📍 Yetib keldi"
STATUS_DONE = "✅ Tugallandi"
STATUS_CANCEL = "❌ Bekor qilindi"

def calc_distance(a, b):
    try:
        lat1, lon1 = map(float, a.split(","))
        lat2, lon2 = map(float, b.split(","))
        R = 6371

        dlat = math.radians(lat2-lat1)
        dlon = math.radians(lon2-lon1)

        x = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(x), math.sqrt(1-x))

        return round(R * c, 2)
    except:
        return 5

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    cursor.execute("SELECT name FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    # User royhatdan o'tgan bolsa
    if user:
        context.user_data["name"] = user[0]

        cursor.execute(
            "SELECT phone FROM users WHERE user_id=?",
            (user_id,)
        )

        phone = cursor.fetchone()

        if phone:
            context.user_data["phone"] = phone[0]

        update.message.reply_text(
            f"👋 Salom {user[0]}!\n🚕 Taksi botga xush kelibsiz",
            reply_markup=main_menu
        )

        return ConversationHandler.END

    # Yangi bolsa user
    update.message.reply_text(
        "👋 Assalomu alaykum!\nIsmingizni kiriting:"
    )

    return NAME
def menu(update, context):
    update.message.reply_text(
        "📍 Qayerdasiz?",
        reply_markup=from_
    )
    return FROM

def get_name(update: Update, context: CallbackContext):
    context.user_data["name"] = update.message.text

    update.message.reply_text(
        "📞 Telefon raqam yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Raqam", request_contact=True)]],
            resize_keyboard=True
        )
    )
    return PHONE


def get_phone(update: Update, context: CallbackContext):
    user = update.message.from_user
    phone = update.message.contact.phone_number
    context.user_data["phone"] = phone

    cursor.execute("""
        INSERT OR REPLACE INTO users(user_id,name,phone,created_at)
        VALUES(?,?,?,?)
    """, (user.id, context.user_data["name"], phone, str(datetime.datetime.now())))

    db.commit()

    update.message.reply_text("✅ Ro‘yxatdan o‘tdingiz!", reply_markup=main_menu)
    return ConversationHandler.END
def get_from(update: Update, context: CallbackContext):


    if update.message.location:
        loc = update.message.location
        context.user_data["from"] = f"{loc.latitude},{loc.longitude}"

    elif update.message.text:
        context.user_data["from"] = update.message.text

    update.message.reply_text(
        "📍 Qayerga borasiz?"
    )

    return TO


def get_to(update: Update, context: CallbackContext):
    context.user_data["to"] = update.message.text

    update.message.reply_text(
        "✍ Qo‘shimcha izoh kiriting:\n\n"
        "Masalan: Yuklarimiz bor"
    )

    return COMMENT

def cancel_order(context: CallbackContext):
    job = context.job
    order_id = job.context

    cursor.execute(
        "UPDATE orders SET status=? WHERE id=?",
        ("❌ Haydovchi topilmadi", order_id)
    )
    db.commit()

def get_comment(update: Update, context: CallbackContext):
    context.user_data["comment"] = update.message.text

    update.message.reply_text(
        "🚕 Tarif tanlang:",
        reply_markup=tarif_
    )

    return TARIF

def tariffs(update: Update, context: CallbackContext):
    update.message.reply_text(
        "💰 Tariflar:\n\n"
        "🚕 Ekonom\n"
        "➡ Boshlanish: 8000 so‘m\n"
        "➡ 1 km: 5000 so‘m\n\n"
        "🚘 Komfort\n"
        "➡ Boshlanish: 10000 so‘m\n"
        "➡ 1 km: 8000 so‘m"
    )

def settings(update: Update, context: CallbackContext):
    update.message.reply_text(
        "⚙ Sozlamalar bo‘limi"
    )

def help_func(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🆘 Yordam:\n\n"
        "🚕 Taksi chaqirish uchun menyudan foydalaning."
    )


def get_tarif(update: Update, context: CallbackContext):
    tarif = update.message.text

    from_loc = context.user_data["from"]
    to_loc = context.user_data["to"]

    try:

        lat1, lon1 = map(float, from_loc.split(","))
        lat2, lon2 = map(float, to_loc.split(","))


        distance = round(((lat1 - lat2)**2 + (lon1 - lon2)**2) ** 0.5 * 111, 2)

    except:
        distance = 5

    # tarif tanlash
    t = TARIFLAR.get(tarif, TARIFLAR["🚕 Ekonom"])
    price = int(t["base"] + distance * t["per_km"])

    # user_data saqlash
    context.user_data["tarif"] = tarif
    context.user_data["distance"] = distance
    context.user_data["price"] = price

    update.message.reply_text(
        f"🚕 BUYURTMA:\n\n"
        f"👤 Ism: {context.user_data.get('name','Nomaʼlum')}\n"
        f"📞 Tel: {context.user_data.get('phone','Nomaʼlum')}\n"
        f"📍 From: {from_loc}\n"
        f"📍 To: {to_loc}\n"
        f"📏 Masofa: {distance} km\n"
        f"💰 Narx: {price} so‘m\n\n"
        f"✔ Tasdiqlaysizmi? (ha/yo‘q)"
    )

    return CONFIRM

def confirm(update: Update, context: CallbackContext):
    if update.message.text.lower() != "ha":
        update.message.reply_text("❌ Bekor qilindi", reply_markup=main_menu)
        return ConversationHandler.END

    if context.user_data.get("lock_confirm"):
        return ConversationHandler.END

    context.user_data["lock_confirm"] = True

    user = update.message.from_user

    cursor.execute("""
                   INSERT INTO orders(user_id, name, phone, from_loc, to_loc,
                                      tarif, distance, price, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   """, (
                       user.id,
                       context.user_data["name"],
                       context.user_data["phone"],
                       context.user_data["from"],
                       context.user_data["to"],
                       context.user_data["tarif"],
                       context.user_data["distance"],
                       context.user_data["price"],
                       STATUS_PENDING,
                       str(datetime.datetime.now())
                   ))
    db.commit()
    order_id = cursor.lastrowid

    # Userga
    update.message.reply_text(
    "🚕 <b>BUYURTMA QABUL QILINDI!</b>\n"
    "━━━━━━━━━━━━━━\n\n"
    f"🆔 <b>#{order_id}</b>\n"
    f"👤 <b>{context.user_data['name']}</b>\n"
    f"📞 {context.user_data['phone']}\n\n"
    f"📍 <b>Qayerdan:</b> {context.user_data['from']}\n"
    f"📍 <b>Qayerga:</b> {context.user_data['to']}\n\n"
    f"✍ Izoh: {context.user_data['comment']}\n\n"
    f"📏 Masofa: <b>{context.user_data['distance']} km</b>\n"
    f"💰 Narx: <b>{context.user_data['price']} so‘m</b>\n\n"
    "━━━━━━━━━━━━━━\n"
    "📡 Status: ⏳ Driver qidirilmoqda...\n\n"
    "🚗 Tez orada haydovchi biriktiriladi!",
    parse_mode="HTML"
)

    # Driverga boradi
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Qabul qilish",
                callback_data=f"accept_{order_id}"
            )
        ]
    ])

    for driver in DRIVERS:
        context.bot.send_message(
            chat_id=driver,
            text=
            f"🚕 YANGI BUYURTMA\n\n"
            f"🆔 #{order_id}\n"
            f"👤 {context.user_data['name']}\n"
            f"📞 {context.user_data['phone']}\n\n"
            f"📍 {context.user_data['from']}\n"
            f"➡ {context.user_data['to']}\n\n"
            f"💬 {context.user_data['comment']}\n\n"
            f"💰 {context.user_data['price']} so‘m",
            reply_markup=keyboard
        )

    context.user_data.clear()
    return ConversationHandler.END


   #   Admin ucn
   #   context.bot.send_message(
   #      chat_id=ADMIN_ID,
   #      text=
   #      f"🚕 YANGI BUYURTMA\n\n"
   #      f"🆔 #{order_id}\n"
   #      f"👤 {context.user_data['name']}\n"
   #      f"📞 {context.user_data['phone']}\n\n"
   #      f"📍 {context.user_data['from']}\n"
   #      f"➡ {context.user_data['to']}\n\n"
   #      f"💬 Izoh: {context.user_data['comment']}\n\n"
   #      f"💰 {context.user_data['price']} so‘m\n"
   #      f"📡 {STATUS_PENDING}"
   #  )
   #  context.user_data.clear()
   #  return ConversationHandler.END

def accept_order(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    driver_id = query.from_user.id

    order_id = int(query.data.split("_")[1])

    cursor.execute("""
                   UPDATE orders
                   SET status=?,
                       driver_id=?
                   WHERE id = ?
                   """, (
                       STATUS_ACCEPTED,
                       driver_id,
                       order_id
                   ))

    db.commit()

    cursor.execute("""
                   SELECT user_id
                   FROM orders
                   WHERE id = ?
                   """, (order_id,))

    user_id = cursor.fetchone()[0]

    context.bot.send_message(
        chat_id=user_id,
        text=
        f"🚗 Driver topildi!\n\n"
        f"🆔 Buyurtma: #{order_id}\n"
        f"📡 Status: {STATUS_ACCEPTED}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛣 Yo‘lda",
                callback_data=f"onway_{order_id}"
            )
        ]
    ])

    query.edit_message_text(
        f"✅ Buyurtma qabul qilindi\n🆔 #{order_id}",
        reply_markup=keyboard
    )

def onway_order(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])

    cursor.execute("""
        UPDATE orders
        SET status=?
        WHERE id=?
    """, (
        STATUS_ONWAY,
        order_id
    ))

    db.commit()

    cursor.execute("""
        SELECT user_id
        FROM orders
        WHERE id=?
    """, (order_id,))

    user_id = cursor.fetchone()[0]

    context.bot.send_message(
        chat_id=user_id,
        text=
        f"🛣 Haydovchi yo‘lda!\n\n"
        f"🆔 Buyurtma: {order_id}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📍 Yetib keldi",
                callback_data=f"arrived_{order_id}"
            )
        ]
    ])

    query.edit_message_text(
        f"🛣 Driver yo‘lda\n🆔 #{order_id}",
        reply_markup=keyboard
    )

def arrived_order(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])

    cursor.execute("""
        UPDATE orders
        SET status=?
        WHERE id=?
    """, (
        STATUS_ARRIVED,
        order_id
    ))

    db.commit()

    cursor.execute("""
        SELECT user_id
        FROM orders
        WHERE id=?
    """, (order_id,))

    user_id = cursor.fetchone()[0]

    context.bot.send_message(
        chat_id=user_id,
        text=
        f"📍 Haydovchi yetib keldi!\n\n"
        f"🆔 Buyurtma: #{order_id}"
    )

    query.edit_message_text(
        f"📍 Driver yetib keldi\n🆔 #{order_id}"
    )

def my_orders(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    cursor.execute("""
        SELECT id, from_loc, to_loc, price, status
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))

    orders = cursor.fetchall()

    if not orders:
        update.message.reply_text("📭 Sizda buyurtmalar yo‘q")
        return

    text = "📦 Mening buyurtmalarim:\n\n"

    for o in orders:
        text += (
            f"🆔 #{o[0]}\n"
            f"📍 {o[1]} → {o[2]}\n"
            f"💰 {o[3]} so‘m\n"
            f"📡 {o[4]}\n\n"
        )

    update.message.reply_text(text)

def admin_panel(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return

    update.message.reply_text("👨‍💼 Admin panel", reply_markup=admin_menu)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    reg = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
            PHONE: [MessageHandler(Filters.contact, get_phone)],
        },
        fallbacks=[]
    )

    order = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex("^🚕 Taksi chaqirish$"), menu)
        ],
        states={
            FROM: [MessageHandler((Filters.text | Filters.location) & ~Filters.command & ~Filters.regex("^(📦|💰|⚙|🆘)"), get_from)],
            TO: [MessageHandler((Filters.text | Filters.location) & ~Filters.command, get_to)],
            COMMENT: [MessageHandler(Filters.text, get_comment)],
            TARIF: [MessageHandler(Filters.text & ~Filters.command, get_tarif)],
            CONFIRM: [MessageHandler(Filters.regex("(ha|yo‘q)"), confirm)]
        },
        fallbacks=[]
    )

    dp.add_handler(reg)
    dp.add_handler(order)

    dp.add_handler(MessageHandler(Filters.regex("^📦 Buyurtmalarim$"), my_orders))
    dp.add_handler(MessageHandler(Filters.regex("^💰 Tariflar$"), tariffs))
    dp.add_handler(MessageHandler(Filters.regex("^⚙ Sozlamalar$"), settings))
    dp.add_handler(MessageHandler(Filters.regex("^🆘 Yordam$"), help_func))

    dp.add_handler(CommandHandler("admin", admin_panel))

    dp.add_handler(CallbackQueryHandler(accept_order, pattern="^accept_"))
    dp.add_handler(CallbackQueryHandler(onway_order, pattern="^onway_"))
    dp.add_handler(CallbackQueryHandler(arrived_order, pattern="^arrived_"))


    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()