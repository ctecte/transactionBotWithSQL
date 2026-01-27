# Telebot expense tracker
<img width="1556" height="1250" alt="image" src="https://github.com/user-attachments/assets/343a3f74-2707-4d85-92e7-1681a01c863b" />

Demo @transactionSQLbot

This telebot utilises pyTelegramBotAPI to connect to a BotAccount created by BotFather.
CommandHandlers take in user input to track spending expenditures in specific categories such as /food, /drink, /grocery, /item

Data is stored in a MySQL 8.1 database docker image, with users able to perform CRUD functions on it. 
Backend python script interacts with the MySQL database to insert and fetch records for users.

Records are kept private by allowing access to only the specific chat_id that is established when user first interacts with the bot. ie You cannot see other peoples' transactions

<img width="1189" height="960" alt="image" src="https://github.com/user-attachments/assets/d658d105-701b-44c1-8692-7b51333e5dd3" />

Summary function to provide insight into daily spendings
