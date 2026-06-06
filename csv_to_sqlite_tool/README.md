# CSV в SQLite на Python

Это учебная утилита, которая берет CSV-файл, автоматически создает таблицу SQLite по заголовкам CSV и вставляет все строки в базу данных.

Проект специально сделан как маленькое ядро. Потом к нему можно подключить GUI, сайт, API или мобильное приложение.

## Быстрый запуск

```powershell
python csv_to_sqlite.py examples/users.csv
```

После запуска появится файл:

```text
examples/users.sqlite3
```

Проверить данные можно так:

```powershell
python -c "import sqlite3; con=sqlite3.connect('examples/users.sqlite3'); print(con.execute('select * from users').fetchall())"
```

## Запуск с параметрами

```powershell
python csv_to_sqlite.py examples/users.csv --database data.sqlite3 --table users
```

CSV с точкой с запятой:

```powershell
python csv_to_sqlite.py data.csv --delimiter ";"
```

Интерактивный режим:

```powershell
python csv_to_sqlite.py --interactive
```

Если таблица уже есть:

```powershell
python csv_to_sqlite.py data.csv --if-exists replace
python csv_to_sqlite.py data.csv --if-exists append
python csv_to_sqlite.py data.csv --if-exists fail
```

Если в CSV есть плохие строки с неправильным количеством ячеек:

```powershell
python csv_to_sqlite.py data.csv --skip-bad-rows
```

## Что делает программа

1. Проверяет, что CSV-файл существует.
2. Читает первую строку как заголовки колонок.
3. Превращает заголовки в безопасные имена колонок SQLite.
4. Автоматически определяет разделитель: `,`, `;`, табуляция или `|`.
5. Создает таблицу в SQLite.
6. Добавляет строки через параметризованные SQL-запросы.
7. Показывает результат: база, таблица, колонки, сколько строк импортировано.
