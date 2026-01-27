# Telebot expense tracker

Demo @transactionSQLbot

This telebot utilises pyTelegramBotAPI to connect to a BotAccount created by BotFather.
CommandHandlers take in user input to track spending expenditures in specific categories such as /food, /drink, /grocery, /item

Data is stored in a MySQL 8.1 database docker image, with users able to perform CRUD functions on it. 
Backend python script interacts with the MySQL database to insert and fetch records for users.

Records are kept private by allowing access to only the specific chat_id that is established when user first interacts with the bot. ie You cannot see other peoples' transactions

