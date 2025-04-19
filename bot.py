import telebot
from datetime import datetime, timedelta
import configparser
import MySQLdb
import re
import logging
from collections import defaultdict
from telebot.types import BotCommand

config = configparser.ConfigParser()
config.read('config.ini')
bot_token = config.get('default', 'bot_token')
HOSTNAME = config.get('default', 'hostname')
USERNAME = config.get('default', 'username')
PASSWORD = config.get('default', 'password')
DATABASE = config.get('default', 'database')

# create an instance of bot
bot = telebot.TeleBot(bot_token)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

conn = None
cursor = None

@bot.message_handler(commands=["select"])
def handle_select_query(message):
    chat_id = message.chat.id
    query = message.text.replace("/select", "", 1).strip()

    if not query.lower().startswith("select"):
        bot.reply_to(message, "❌ Only SELECT queries are allowed.")
        return

    try:
        cursor.execute(query)
        results = cursor.fetchall()

        if not results:
            bot.reply_to(message, "No results found.")
            return

        msg = f"📝 Results:\n\n"
        for row in results[:10]:  # limit to 10 rows
            msg += "▫️ " + " | ".join(str(col) for col in row) + "\n"
        
        if len(results) > 10:
            msg += f"...and {len(results)-10} more rows."

        bot.send_message(chat_id, msg)

    except Exception as e:
        bot.reply_to(message, f"❌ Query failed:\n{str(e)}")


def format_message(results):
    grouped = defaultdict(list)
    for row in results:
        date_str = row[1].strftime("%d-%m-%y")
        grouped[date_str].append(row)

    msg = "📆\n"

    for date in sorted(grouped):
        msg += f"{date}\n"
        for row in grouped[date]:
            # Truncate name if it's longer than 15 characters
            name = row[2][:11] + ".." if len(row[2]) > 13 else row[2]
            cost = f"${row[3]:.2f}"
            qty = f"x{row[4]}" 
            item_type = row[5].capitalize()

            # Align all parts nicely to prevent wrapping
            msg += f"▫️{name:<13} {cost} {qty:<3}{item_type}\n"
        msg += "\n"
    return msg

@bot.message_handler(commands=['month'])
def select_month(message):
    chat_id = message.chat.id
    text = message.text
    try:
        first_day = datetime.today().replace(day=1)
        cursor.execute ("SELECT * from transactions where date >= %s order by date", (first_day,))
        results = cursor.fetchall()

        if not results:
            bot.reply_to(message, f"No transactions found since {first_day}.")
            return
        else:
            msg = format_message(results)
            final_msg = f"📆 This month's Transactions:\n\n```{msg}```"
            bot.send_message(chat_id, final_msg, parse_mode="Markdown")    
    except Exception as e:
        bot.send_message(chat_id, f"error {str(e)}")
        logger.info(f"select specific error :{str(e)}")

@bot.message_handler(commands=['week', 'today','yesterday'])
def select_specific(message):
    chat_id = message.chat.id
    text = message.text
    try:
        command = "Today"
        timeDelta = 0
        if ("week" in text):
            timeDelta = 7
            command = "Week"
        elif ("yesterday" in text):
            timeDelta = 1
            command = "Yesterday"
        today = datetime.today().date()
        dateToFind = today - timedelta(days=timeDelta)
        cursor.execute ("SELECT * from transactions where date >= %s order by date", (dateToFind,))
        results = cursor.fetchall()

        if not results:
            bot.reply_to(message, f"No transactions found since {dateToFind}.")
            return
        else:
            msg = format_message(results)
            final_msg = f"📆 {command}'s Transactions:\n\n```{msg}```"
            bot.send_message(chat_id, final_msg, parse_mode="Markdown")    
    except Exception as e:
        bot.send_message(chat_id, f"error {str(e)}")
        logger.info(f"select specific error :{str(e)}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Hi, I'm a transaction bot using a MySQL database to store your information")

def update_db(chat_id, transaction_id, column, new_value):
    try:
        query = f"UPDATE transactions SET {column} = %s WHERE id = %s"
        cursor.execute(query, (new_value, transaction_id))
        conn.commit()
        bot.send_message(chat_id, f"✅ Updated {column} of entry {transaction_id} to '{new_value}'")
        logger.info(f"✅ Updated {column} of entry {transaction_id} to '{new_value}'")
    except Exception as e:
        bot.send_message(chat_id, f"Something went wrong: {str(e)}")
        logger.info(f"Update error: {str(e)}")

@bot.message_handler(commands=['delete'])
def delete(message):
    text = message.text
    match = re.match(r"^/delete\s+(\d+)$", text)

    if not match:
        bot.reply_to(message, "❌ Invalid format. Use: /delete <id>")
        return

    transaction_id = int(match.group(1))
    try:
        cursor.execute("DELETE FROM transactions WHERE id = %s", (transaction_id,))
        conn.commit()
        bot.reply_to(message, f"✅ Entry {transaction_id} deleted.")
        logging.info(f"Entry {transaction_id} deleted.")
    except Exception as e:
        bot.reply_to(message, f"{str(e)}")
        logging.info( f"{str(e)}")

@bot.message_handler(commands=['update'])
def update(message):
    chat_id = message.chat.id
    text = text = message.text.replace("/update", "", 1).strip()
    match = re.match(r"^(\d+)\s+(\w+)\s+(.+)$", text)
    # expecting /update <id> <column_name> <data>
    # /update 3 name Chicken Rice
    # /update 4 date 101203
    if not match:
        bot.reply_to(message, "❌ Invalid format. \nUse: /update <id> <column_name> <data>")
        return
    
    transaction_id = int(match.group(1))
    column = match.group(2).lower()
    new_value = match.group(3).strip()

    try:
        if column == 'date':
            new_value = datetime.strptime(new_value, "%d%m%y").date()
        elif column == 'cost':
            new_value = float(new_value)
        elif column == 'quantity':
            new_value = int(new_value)
        update_db(chat_id, transaction_id, column, new_value)
    except Exception as e:
        bot.send_message(chat_id, {str(e)})
        logger.info({str(e)})
    

def insert_into_db(chat_id, date, cost, name, quantity, item_type):
    try :
        # check if there is an entry of this item here already
        cursor.execute("SELECT quantity from transactions where date = %s and name = %s", (date,name,))
        result = cursor.fetchone()

        if result is None:
            cursor.execute("""
                        INSERT INTO transactions (date, name, cost, quantity, type) 
                        values (%s, %s, %s, %s, %s)
                        """,
                        (date, name, cost, quantity, item_type))
        else :
            current_quantity = result[0]
            updated_quantity = int(current_quantity) + quantity
            cursor.execute("""UPDATE transactions set quantity = %s
                            where date = %s and name = %s
                            """, (updated_quantity, date, name))
        
        conn.commit()
    except Exception as e:
        bot.send_message(chat_id, f"failed to insert: {str(e)}")
        logger.info(f"Insert or update error: {str(e)}")

def get_item_type(message_text):
    message_text = message_text.lower()
    if "food" in message_text:
        return "Food"
    elif "drink" in message_text:
        return "Drink"
    elif "grocery" in message_text:
        return "Groceries"
    elif "item" in message_text:
        return "Item"
    elif "dessert" in message_text:
        return "Dessert"
    else:
        return "Others"

@bot.message_handler(commands=['backdate'])
def backdate(message):
    chat_id = message.chat.id
    # remove the /backdate
    text = message.text.replace("/backdate", "", 1).strip()
    try:
        # Match format: 120425 food $5.00 Chicken Rice x2
        match = re.match(r"(\d{6})\s+(\w+)\s+\$(\d+(?:\.\d{2})?)\s+(.+?)(?:\s+x(\d+))?$", text)
        if not match:
            bot.reply_to(message, "❌ Invalid format. Use: /backdate <DDMMYY> <type> $<cost> <name> x<Qty>")
            return
        
        date_str = match.group(1)     # '120425'
        item_type = match.group(2)    # 'food'
        cost = float(match.group(3))  # 6.90
        name = match.group(4)         # 'Chicken Rice'
        quantity = int(match.group(5)) if match.group(5) else 1

        # Convert DDMMYY to datetime.date
        date = datetime.strptime(date_str, "%d%m%y").date()
        insert_into_db(chat_id, date, cost, name, quantity, item_type)
        bot.reply_to(message, f"✅ Backdated transaction for {name} on {date} added!")
    except Exception as e:
        logger.error(f"Backdate error: {str(e)}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=["food", "drink", "item", "grocery", "dessert"])
def parse_message(message):
    chat_id = message.chat.id
    
    # regex out the contents
    item_type = get_item_type(message.text.lower())
    # remove the /whatever from the message
    command = message.text.split(" ", 1)[0]
    transaction_text = message.text.replace(command, "", 1).strip()
    match = re.match(r"\$(\d+(?:\.\d{2})?)\s+(.+?)(?:\s+x(\d+))?$", transaction_text)
    
    if match:
        cost = float(match.group(1))  # Convert cost to float
        name = match.group(2)  # Extract name string
        # print(name)
        quantity = 1
        if match.group(3):
            quantity = int(match.group(3))  # Convert quantity to int
        logger.info("parsed successfully")
        
        logger.info({"cost": cost, "name": name, "quantity": quantity})
        today = datetime.today().date()
        insert_into_db(chat_id, today, cost, name, quantity, item_type)
        bot.reply_to(message, "Transaction added")
    else:
        bot.reply_to(message,
            "❌ Invalid format!\n\n"
            "💡 Please enter your transaction like this:\n"
            "`/food $5.50 Chicken Rice x2`\n\n"
            "📌 Format:\n"
            "`/<type>` - One of: food, drink, item, grocery\n"
            "`$<amount>` - Cost (with $ sign)\n"
            "`<name>` - Name of the item\n"
            "`x<quantity>` - Optional (defaults to 1)\n\n"
            "✅ Example:\n"
            "`/drink $3.00 Iced Milo`\n"
            "`/grocery $7.20 Eggs x2`",
            parse_mode="Markdown")


def create_database(cursor, query):
    try:
        cursor.execute(query)
        logger.info("Successfully created database")
    except Exception as e:
        logger.info(f"Error: {str(e)}")

if __name__ == '__main__':
    try:
        # connect to the server
        conn_mysql = MySQLdb.connect(host=HOSTNAME, user=USERNAME, passwd=PASSWORD)
        # create cursor in sql
        cursor_mysql = conn_mysql.cursor()
        query = "CREATE DATABASE IF NOT EXISTS " + DATABASE
        create_database(cursor_mysql, query)

        # connect to the database after created, and assign global variable
        conn = MySQLdb.connect(host=HOSTNAME, user=USERNAME, passwd=PASSWORD, db=DATABASE)
        cursor = conn.cursor()

        # create transactions table
        sql_command = """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            date DATE,
            name VARCHAR(45),
            cost DECIMAL(6,2),
            quantity INT,
            type VARCHAR(10)
        );
        """
        cursor.execute(sql_command)
        logger.info("transactions table created")
        bot.set_my_commands([
            BotCommand("start", "Show welcome message"),
            BotCommand("help", "Show usage guide"),
            BotCommand("food", "Add a food transaction"),
            BotCommand("drink", "Add a drink transaction"),
            BotCommand("dessert", "Add a dessert transaction"),
            BotCommand("item", "Add a miscellaneous item"),
            BotCommand("grocery", "Add a grocery transaction"),
            BotCommand("backdate", "Add a backdated transaction"),
            BotCommand("week", "Show this week's transactions"),
            BotCommand("month", "Show this month's transactions"),
            BotCommand("yesterday", "Show yesterday's transactions"),
            BotCommand("select", "Run a SELECT SQL query"),
            BotCommand("update", "Update a transaction field"),
            BotCommand("delete", "Delete a transaction by ID"),
        ])
        logger.info("Bot started..")
        bot.infinity_polling()
    except Exception as e:
        print(f"Error: {str(e)}")
